#!/usr/bin/env python3
"""Validate a source-bound vpsctl Debian package before privileged installation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tomllib


def validate(package, version, commit):
    package = Path(package)
    if package.is_symlink() or not package.is_file() or package.stat().st_size > 64 * 1024**2:
        raise ValueError('vpsctl package must be a regular file <=64 MiB')
    if not re.fullmatch(r'\d+\.\d+\.\d+', version) or not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Invalid expected vpsctl version/commit')
    def field(name):
        return subprocess.check_output(['dpkg-deb', '-f', str(package), name], text=True).strip()
    expected = {'Package': 'vpsctl', 'Version': version, 'Architecture': 'amd64',
                'X-Vpsctl-Source-Commit': commit, 'X-Vpsctl-Source-Dirty': 'false'}
    for name, value in expected.items():
        if field(name) != value:
            raise ValueError('vpsctl package provenance mismatch: ' + name)
    allowed = {'usr/bin/vpsctl', 'usr/share/doc/vpsctl/README.md', 'usr/share/doc/vpsctl/copyright',
               'usr/share/man/man1/vpsctl.1.gz', 'usr/share/bash-completion/completions/vpsctl',
               'usr/share/zsh/vendor-completions/_vpsctl'}
    # cap decompression by streaming the tar rather than buffering a tar bomb.
    for flag, controls in [('--ctrl-tarfile', True), ('--fsys-tarfile', False)]:
        child = subprocess.Popen(['dpkg-deb', flag, str(package)], stdout=subprocess.PIPE)
        total = 0
        found = set()
        try:
            with tarfile.open(fileobj=child.stdout, mode='r|') as archive:
                for entry in archive:
                    name = entry.name.removeprefix('./').rstrip('/')
                    if name in ('', '.') and entry.isdir():
                        continue
                    parts = Path(name).parts
                    if name.startswith('/') or '..' in parts or entry.issym() or entry.islnk():
                        raise ValueError('Unsafe path in vpsctl package')
                    if entry.isdir():
                        if entry.mode & 0o7777 != 0o755 or controls:
                            raise ValueError('Unexpected package directory permissions/control directory')
                        if not controls and not any(file.startswith(name + '/') for file in allowed):
                            raise ValueError('Unexpected package directory')
                        continue
                    if not entry.isfile() or name in found or entry.mode & 0o7022:
                        raise ValueError('Unexpected or privileged package entry')
                    total += entry.size
                    if total > 32 * 1024**2:
                        raise ValueError('Expanded vpsctl package exceeds limit')
                    found.add(name)
                    if controls:
                        if name != 'control':
                            raise ValueError('Maintainer scripts/control hooks forbidden')
                    elif name not in allowed:
                        raise ValueError('Unexpected vpsctl package payload')
                    elif name == 'usr/bin/vpsctl':
                        header = archive.extractfile(entry).read(64)
                        if len(header) < 64 or header[:6] != b'\x7fELF\x02\x01' or header[18:20] != b'\x3e\x00' or entry.mode & 0o777 != 0o755:
                            raise ValueError('Expected non-setuid amd64 ELF executable')
            if child.wait() != 0 or found != ({'control'} if controls else allowed):
                raise ValueError('Incomplete vpsctl package payload')
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
            child.stdout.close()
    return {'version': version, 'source_commit': commit,
            'package_file': f'vpsctl_{version}_amd64.deb',
            'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest()}


def from_source(source, package=None):
    source = Path(source).resolve()
    version = tomllib.loads((source / 'vpsctl/Cargo.toml').read_text())['package']['version']
    commit = subprocess.check_output(['git', '-c', f'safe.directory={source}', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    package = Path(package) if package else source / 'vpsctl/dist' / f'vpsctl_{version}_amd64.deb'
    return package, validate(package, version, commit)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        path, metadata = from_source(args.source, args.package)
        print(json.dumps(metadata) if args.json else path.resolve())
    except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError) as error:
        parser.exit(1, f'vpsctl package rejected: {error}. Run ./vpsctl/scripts/package-deb.sh from a clean checkout.\n')

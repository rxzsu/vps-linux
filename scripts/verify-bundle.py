#!/usr/bin/env python3
"""Verify mandatory manifest coverage, actual bytes and SPDX/source coherence."""
import hashlib
import json
import pathlib
import re
import sys
import subprocess
import tarfile
from sbom import generate
from vpsctl_package import validate as validate_vpsctl


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def regular(bundle, name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name):
        raise ValueError('Unsafe manifest filename: ' + name)
    path = bundle / name
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing regular bundle file: ' + name)
    return path


def checksum_entries(path):
    entries = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r'([a-f0-9]{64}) [ *]([A-Za-z0-9][A-Za-z0-9._-]*)', line)
        if not match or match[2] in entries:
            raise ValueError('Malformed or duplicate checksum entry')
        entries[match[2]] = match[1]
    return entries


def verify(bundle):
    manifest = regular(bundle, 'SHA256SUMS')
    metadata = json.loads(regular(bundle, 'build.json').read_text())
    version = metadata.get('version', '')
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+(-dev)?', version):
        raise ValueError('Invalid version in build metadata')
    commit = metadata.get('source_commit', '')
    if not isinstance(commit, str) or not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Missing full source commit in metadata')
    image = 'vps-linux-v' + version + '.qcow2'
    required = {image, image + '.sha256', 'build.json', 'packages.tsv', 'sbom.spdx.json'}
    utility = metadata.get('vpsctl')
    if tuple(map(int, version.removesuffix('-dev').split('.'))) >= (0, 4) and not isinstance(utility, dict):
        raise ValueError('v0.4+ bundles require vpsctl provenance')
    if utility is not None:
        if not isinstance(utility, dict) or not re.fullmatch(r'vpsctl_[0-9]+\.[0-9]+\.[0-9]+_amd64\.deb', utility.get('package_file', '')):
            raise ValueError('Invalid vpsctl package metadata')
        required.add(utility['package_file'])
    entries = checksum_entries(manifest)
    if not required <= entries.keys():
        raise ValueError('SHA256SUMS omits mandatory files: ' + ', '.join(sorted(required - entries.keys())))
    for name, expected in entries.items():
        if digest(regular(bundle, name)) != expected:
            raise ValueError('SHA256 mismatch: ' + name)
    if metadata.get('image_sha256') != entries[image]:
        raise ValueError('Image metadata digest mismatch')
    if metadata.get('package_manifest_sha256') != entries['packages.tsv']:
        raise ValueError('Package manifest metadata digest mismatch')
    if checksum_entries(regular(bundle, image + '.sha256')) != {image: entries[image]}:
        raise ValueError('Image sidecar checksum does not describe exactly this image')
    if utility is not None:
        actual = validate_vpsctl(regular(bundle, utility['package_file']), utility.get('version', ''), commit)
        if actual != utility or entries[utility['package_file']] != utility['package_sha256']:
            raise ValueError('vpsctl provenance/hash mismatch')
        rows = (bundle / 'packages.tsv').read_text().splitlines()
        if f"vpsctl\t{utility['version']}\tamd64" not in rows:
            raise ValueError('Installed vpsctl missing from package manifest')
    sbom = json.loads(regular(bundle, 'sbom.spdx.json').read_text())
    expected = generate((bundle / 'packages.tsv').read_bytes(), version, commit,
                        metadata['created_utc'])
    if sbom != expected:
        raise ValueError('SBOM differs from the package manifest, source or content namespace')
    return bundle / image


if __name__ == '__main__':
    try:
        candidate = pathlib.Path(sys.argv[1])
        if candidate.is_symlink() or not candidate.is_dir():
            raise ValueError('Bundle must be a real directory')
        print(verify(candidate.resolve()))
    except (ValueError, OSError, KeyError, TypeError, IndexError, AttributeError, UnicodeError, subprocess.CalledProcessError, tarfile.TarError) as error:
        sys.exit(str(error))

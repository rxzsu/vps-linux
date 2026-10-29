"""Actual Debian package validation and v0.5 bundle coverage, without root."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from vpsctl_package import validate
from sbom import generate
SPEC = importlib.util.spec_from_file_location('v04_verifier', ROOT / 'scripts/verify-bundle.py')
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class VpsctlImage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.commit = 'a' * 40
        self.version = '0.5.0'
        self.tree = self.root / 'tree'
        (self.tree / 'DEBIAN').mkdir(parents=True)
        (self.tree / 'usr/bin').mkdir(parents=True)
        (self.tree / 'usr/share/doc/vpsctl').mkdir(parents=True)
        (self.tree / 'usr/share/man/man1').mkdir(parents=True)
        (self.tree / 'usr/share/bash-completion/completions').mkdir(parents=True)
        (self.tree / 'usr/share/zsh/vendor-completions').mkdir(parents=True)
        self.control = f'Package: vpsctl\nVersion: {self.version}\nArchitecture: amd64\nMaintainer: Test <test@example.invalid>\nDescription: Fixture\nX-Vpsctl-Source-Commit: {self.commit}\nX-Vpsctl-Source-Dirty: false\n'
        (self.tree / 'DEBIAN/control').write_text(self.control)
        shutil.copy('/bin/true', self.tree / 'usr/bin/vpsctl')
        (self.tree / 'usr/bin/vpsctl').chmod(0o755)
        for name in ('README.md', 'copyright'):
            (self.tree / 'usr/share/doc/vpsctl' / name).write_text('fixture\n')
        for name in ('usr/share/man/man1/vpsctl.1.gz', 'usr/share/bash-completion/completions/vpsctl',
                     'usr/share/zsh/vendor-completions/_vpsctl'):
            (self.tree / name).write_text('fixture\n')
        self.package = self.root / 'vpsctl_0.5.0_amd64.deb'
        self.pack()

    def pack(self):
        # Normalize modes so the fixture does not depend on the builder's umask:
        # the real package is built with umask 022 (directories 755, payload 644).
        for entry in self.tree.rglob('*'):
            if entry.is_dir():
                entry.chmod(0o755)
            elif entry.is_file() and self.tree / 'DEBIAN' not in entry.parents and entry != self.tree / 'usr/bin/vpsctl':
                entry.chmod(0o644)
        (self.tree / 'DEBIAN/control').chmod(0o644)
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(self.tree), str(self.package)], check=True, capture_output=True)

    def test_clean_amd64_package_is_accepted_and_hashed(self):
        info = validate(self.package, self.version, self.commit)
        self.assertEqual(info['package_sha256'], hashlib.sha256(self.package.read_bytes()).hexdigest())
        self.assertEqual(info['package_file'], self.package.name)

    def test_stale_dirty_and_wrong_version_packages_are_rejected(self):
        for field, old, new in [('commit', self.commit, 'b' * 40), ('dirty', 'false', 'true'), ('version', '0.5.0', '0.2.0')]:
            with self.subTest(field=field):
                (self.tree / 'DEBIAN/control').write_text(self.control.replace(old, new))
                self.pack()
                with self.assertRaisesRegex(ValueError, 'provenance mismatch'):
                    validate(self.package, self.version, self.commit)

    def test_hooks_and_privileged_binaries_are_rejected(self):
        hook = self.tree / 'DEBIAN/postinst'
        hook.write_text('#!/bin/sh\nexit 0\n')
        hook.chmod(0o755)
        self.pack()
        with self.assertRaises(ValueError):
            validate(self.package, self.version, self.commit)
        hook.unlink()
        (self.tree / 'usr/bin/vpsctl').chmod(0o4755)
        self.pack()
        with self.assertRaises(ValueError):
            validate(self.package, self.version, self.commit)

    def test_unexpected_config_and_symlinks_are_rejected(self):
        (self.tree / 'etc').mkdir()
        (self.tree / 'etc/unsafe.conf').write_text('not allowed')
        self.pack()
        with self.assertRaises(ValueError):
            validate(self.package, self.version, self.commit)
        link = self.root / 'alias.deb'
        link.symlink_to(self.package)
        with self.assertRaises(ValueError):
            validate(link, self.version, self.commit)

    def bundle(self):
        image = self.root / 'vps-linux-v0.5.qcow2'
        subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(image), '8G'], check=True, capture_output=True)
        image_hash = hashlib.sha256(image.read_bytes()).hexdigest()
        (self.root / (image.name + '.sha256')).write_text(f'{image_hash}  {image.name}\n')
        manifest = b'libc6\t2.41\tamd64\nvpsctl\t0.5.0\tamd64\n'
        (self.root / 'packages.tsv').write_bytes(manifest)
        metadata = {'version': '0.5', 'source_commit': self.commit, 'created_utc': '2026-10-29T00:00:00+00:00', 'image_sha256': image_hash, 'package_manifest_sha256': hashlib.sha256(manifest).hexdigest(), 'vpsctl': validate(self.package, self.version, self.commit)}
        (self.root / 'build.json').write_text(json.dumps(metadata))
        (self.root / 'sbom.spdx.json').write_text(json.dumps(generate(manifest, '0.5', self.commit, metadata['created_utc'])))
        self.files = [image.name, image.name + '.sha256', 'packages.tsv', 'build.json', 'sbom.spdx.json', self.package.name]
        self.rehash()
        return image, metadata

    def rehash(self):
        (self.root / 'SHA256SUMS').write_text(''.join(hashlib.sha256((self.root / name).read_bytes()).hexdigest() + '  ' + name + '\n' for name in self.files))

    def test_v04_bundle_requires_covered_package_provenance_and_manifest(self):
        image, metadata = self.bundle()
        self.assertEqual(VERIFIER.verify(self.root), image)
        sbom = json.loads((self.root / 'sbom.spdx.json').read_text())
        package = next(p for p in sbom['packages'] if p['name'] == 'vpsctl')
        self.assertIn('pkg:deb/vps-linux/vpsctl@', package['externalRefs'][0]['referenceLocator'])
        self.files.remove(self.package.name)
        self.rehash()
        with self.assertRaisesRegex(ValueError, 'omits mandatory'):
            VERIFIER.verify(self.root)
        self.files.append(self.package.name)
        del metadata['vpsctl']
        (self.root / 'build.json').write_text(json.dumps(metadata))
        self.rehash()
        with self.assertRaisesRegex(ValueError, 'require vpsctl'):
            VERIFIER.verify(self.root)

    def test_manifest_cannot_claim_a_different_installed_utility(self):
        _, metadata = self.bundle()
        manifest = (self.root / 'packages.tsv').read_bytes().replace(b'0.5.0', b'0.2.0')
        (self.root / 'packages.tsv').write_bytes(manifest)
        metadata['package_manifest_sha256'] = hashlib.sha256(manifest).hexdigest()
        (self.root / 'build.json').write_text(json.dumps(metadata))
        self.rehash()
        with self.assertRaisesRegex(ValueError, 'missing from package manifest'):
            VERIFIER.verify(self.root)

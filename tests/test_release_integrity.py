"""Real QCOW2/minisign tests, plus regression cases for the reviewed v0.3 bugs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from sbom import generate, parse_manifest
from importlib.util import spec_from_file_location, module_from_spec
spec = spec_from_file_location('verify_bundle', ROOT / 'scripts/verify-bundle.py')
verifier = module_from_spec(spec)
spec.loader.exec_module(verifier)


class Bundle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vps-integrity-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.bundle = self.home / 'bundle'
        self.bundle.mkdir()
        self.version = '0.3-dev'
        self.commit = 'a' * 40
        self.created = '2026-10-28T17:00:00+00:00'
        self.image = self.bundle / 'vps-linux-v0.3-dev.qcow2'
        subprocess.run(['qemu-img', 'create', '-f', 'qcow2', str(self.image), '8G'], check=True, capture_output=True)
        self.manifest = b'cloud-init\t25.1.4\tall\nlibc6:amd64\t2.41\tamd64\n'
        (self.bundle / 'packages.tsv').write_bytes(self.manifest)
        image_hash = hashlib.sha256(self.image.read_bytes()).hexdigest()
        (self.bundle / (self.image.name + '.sha256')).write_text(image_hash + '  ' + self.image.name + '\n')
        self.metadata = {'version': self.version, 'source_commit': self.commit, 'created_utc': self.created,
                         'image_sha256': image_hash, 'package_manifest_sha256': hashlib.sha256(self.manifest).hexdigest()}
        (self.bundle / 'build.json').write_text(json.dumps(self.metadata))
        self.sbom = generate(self.manifest, self.version, self.commit, self.created)
        (self.bundle / 'sbom.spdx.json').write_text(json.dumps(self.sbom))
        self.files = [self.image.name, self.image.name + '.sha256', 'packages.tsv', 'build.json', 'sbom.spdx.json']
        self.rehash()
        self.key = self.home / 'private.key'
        self.public = self.home / 'public.pub'
        subprocess.run(['minisign', '-G', '-W', '-p', str(self.public), '-s', str(self.key)], check=True, capture_output=True)
        self.sign()

    def rehash(self, files=None):
        (self.bundle / 'SHA256SUMS').write_text(''.join(
            hashlib.sha256((self.bundle / name).read_bytes()).hexdigest() + '  ' + name + '\n'
            for name in (self.files if files is None else files)))

    def sign(self):
        subprocess.run(['minisign', '-Sm', str(self.bundle / 'SHA256SUMS'), '-s', str(self.key)], check=True, capture_output=True)

    def check(self, public=None):
        return subprocess.run([str(ROOT / 'scripts/verify-release.sh'), str(self.bundle),
                               '--minisign-pubkey', str(public or self.public)], capture_output=True, text=True)

    def test_real_signed_qcow2_bundle_passes(self):
        run = self.check()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('Verified bundle:', run.stdout)

    def test_signed_manifest_cannot_omit_image(self):
        self.rehash(self.files[1:])
        self.sign()
        run = self.check()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('omits mandatory', run.stderr)

    def test_payload_tampering_fails(self):
        with self.image.open('ab') as stream:
            stream.write(b'changed')
        run = self.check()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('SHA256 mismatch', run.stderr)

    def test_signature_tampering_fails_even_with_valid_hash_entries(self):
        path = self.bundle / 'SHA256SUMS'
        path.write_text('\n'.join(reversed(path.read_text().splitlines())) + '\n')
        self.assertEqual(verifier.verify(self.bundle), self.image)
        self.assertNotEqual(self.check().returncode, 0)

    def test_wrong_trust_key_fails(self):
        other_key, other_pub = self.home / 'other.key', self.home / 'other.pub'
        subprocess.run(['minisign', '-G', '-W', '-p', str(other_pub), '-s', str(other_key)], check=True, capture_output=True)
        self.assertNotEqual(self.check(other_pub).returncode, 0)

    def test_unrelated_sbom_with_same_package_count_fails(self):
        self.sbom['packages'][0]['name'] = 'wrong-package'
        (self.bundle / 'sbom.spdx.json').write_text(json.dumps(self.sbom))
        self.rehash()
        with self.assertRaisesRegex(ValueError, 'SBOM differs'):
            verifier.verify(self.bundle)

    def test_false_image_digest_in_metadata_fails(self):
        self.metadata['image_sha256'] = '0' * 64
        (self.bundle / 'build.json').write_text(json.dumps(self.metadata))
        self.rehash()
        with self.assertRaisesRegex(ValueError, 'metadata digest'):
            verifier.verify(self.bundle)

    def test_valid_hashes_do_not_make_a_fake_qcow2_pass(self):
        self.image.write_bytes(b'not a QCOW2')
        value = hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.metadata['image_sha256'] = value
        (self.bundle / 'build.json').write_text(json.dumps(self.metadata))
        (self.bundle / (self.image.name + '.sha256')).write_text(value + '  ' + self.image.name + '\n')
        self.rehash()
        self.sign()
        self.assertNotEqual(self.check().returncode, 0)

    def test_duplicate_and_traversal_manifest_entries_fail(self):
        path = self.bundle / 'SHA256SUMS'
        original = path.read_text()
        for extra in (original.splitlines()[0], '0' * 64 + '  ../outside'):
            path.write_text(original + extra + '\n')
            with self.assertRaisesRegex(ValueError, 'Malformed or duplicate'):
                verifier.verify(self.bundle)

    def test_symlinked_payload_rejected(self):
        outside = self.home / 'outside.qcow2'
        self.image.rename(outside)
        self.image.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'regular bundle file'):
            verifier.verify(self.bundle)


class SBOM(unittest.TestCase):
    def test_changed_manifest_changes_document_namespace(self):
        a = generate(b'example\t1\tall\n', '0.3-dev', 'a' * 40, '2026-10-28T00:00:00Z')
        b = generate(b'example\t2\tall\n', '0.3-dev', 'a' * 40, '2026-10-28T00:00:00Z')
        self.assertNotEqual(a['documentNamespace'], b['documentNamespace'])
        self.assertEqual(a, generate(b'example\t1\tall\n', '0.3-dev', 'a' * 40, '2026-10-28T00:00:00Z'))

    def test_multiarch_all_and_collision_free_ids(self):
        packages = parse_manifest(b'liba+b\t1:2+3\tall\nliba-b\t1\tamd64\nlibc6:amd64\t2\tamd64\nlibc6:arm64\t2\tarm64\n')
        self.assertEqual(len({p['SPDXID'] for p in packages}), 4)
        all_package = next(p for p in packages if p['name'] == 'liba+b')
        self.assertEqual(all_package['externalRefs'][0]['referenceLocator'], 'pkg:deb/debian/liba%2Bb@1%3A2%2B3?arch=all')

    def test_legacy_manifest_does_not_invent_architecture(self):
        package = parse_manifest(b'cloud-init\t25.1\n')[0]
        self.assertNotIn('arch=', package['externalRefs'][0]['referenceLocator'])


class AptPolicy(unittest.TestCase):
    def test_effective_policy_clears_inherited_nonsecurity_origins(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'merged.conf'
            config.write_text('''Unattended-Upgrade::Allowed-Origins { "Debian:stable"; };
Unattended-Upgrade::Origins-Pattern { "origin=Debian,codename=trixie,label=Debian"; };
''' + (ROOT / 'configs/apt/52-vps-linux-unattended-upgrades').read_text())
            run = subprocess.run(['apt-config', '-o', 'Dir::Etc::Parts=-', '-o', 'Dir::Etc::Main=-',
                                  '-c', str(config), 'dump'], capture_output=True, text=True, check=True)
            rules = [line for line in run.stdout.splitlines() if line.startswith('Unattended-Upgrade::Origins-Pattern:: ')]
            self.assertEqual(len(rules), 1)
            self.assertIn('codename=${distro_codename}-security,label=Debian-Security', rules[0])
            self.assertNotIn('Unattended-Upgrade::Allowed-Origins::', run.stdout)

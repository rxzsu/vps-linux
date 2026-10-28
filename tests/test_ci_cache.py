"""CI regressions: read-only release manifests and cache boundaries."""
import pathlib
import subprocess
import tempfile
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / '.github/workflows/validate-build-system.yml').read_text())
STEPS = WORKFLOW['jobs']['build-and-boot']['steps']


class CICache(unittest.TestCase):
    def test_tampering_probe_handles_read_only_manifest(self):
        signing = next(step['run'] for step in STEPS if step.get('name') == 'Sign checksums (keyless)')
        probe = signing
        start = probe.index('cp artifacts/SHA256SUMS artifacts/tampered-checksums')
        end = probe.index('if cosign verify-blob artifacts/tampered-checksums')
        with tempfile.TemporaryDirectory() as directory:
            artifacts = pathlib.Path(directory) / 'artifacts'
            artifacts.mkdir()
            manifest = artifacts / 'SHA256SUMS'
            manifest.write_bytes(b'original manifest\n')
            manifest.chmod(0o444)
            result = subprocess.run(['bash', '-eu', '-c', probe[start:end]], cwd=directory,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(manifest.read_bytes(), b'original manifest\n')
            self.assertEqual(manifest.stat().st_mode & 0o777, 0o444)
            self.assertEqual((artifacts / 'tampered-checksums').read_bytes(), b'original manifest\n\n')

    def test_cache_contains_only_host_packages_and_appliance(self):
        cache = next(step for step in STEPS if step.get('name') == 'Restore host packages and libguestfs appliance')
        self.assertEqual(cache['with']['path'], '.ci-cache/')
        self.assertIn('steps.cache_context.outputs.image', cache['with']['key'])
        self.assertIn('steps.cache_context.outputs.date', cache['with']['key'])
        install = next(step['run'] for step in STEPS if step.get('name') == 'Install host prerequisites')
        build = next(step['run'] for step in STEPS if step.get('name') == 'Build development candidate')
        self.assertIn('.ci-cache/apt', install)
        self.assertIn('LIBGUESTFS_CACHEDIR="$GITHUB_WORKSPACE/.ci-cache/libguestfs"', build)
        self.assertNotIn('if', next(step for step in STEPS if step.get('name') == 'Build development candidate'))
        cleanup = next(step for step in STEPS if step.get('name') == 'Make build cache readable for saving')
        self.assertEqual(cleanup['if'], 'always()')

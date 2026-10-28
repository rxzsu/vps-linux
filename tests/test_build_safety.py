"""Exercise image admission and host cleanup safety without root or virtualization."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_image', ROOT / 'scripts/check-image.py')
image_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_module)


class ImageAdmission(unittest.TestCase):
    def test_plain_eight_gib_qcow2(self):
        image_module.validate({'format': 'qcow2', 'virtual-size': 8 * 1024**3})

    def test_reject_unsafe_or_unexpected_images(self):
        valid = {'format': 'qcow2', 'virtual-size': 8 * 1024**3}
        for change in ({'format': 'raw'}, {'virtual-size': 1},
                       {'backing-filename': '/dev/sda'}, {'encrypted': True},
                       {'dirty-flag': True}, {'data-file': '/dev/nvme0n1'},
                       {'format-specific': {'data': {'corrupt': True}}},
                       {'format-specific': {'data': {'data-file': '/dev/sda'}}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                image_module.validate({**valid, **change})

    def test_cli_preserves_failure(self):
        result = subprocess.run(['python3', str(ROOT / 'scripts/check-image.py')],
                                input=json.dumps({'format': 'raw'}), text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('QCOW2', result.stderr)


class CleanupSafety(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='vps-safety-')
        self.base = Path(self.tmp.name)
        self.output = self.base / 'output'
        self.output.mkdir()
        self.outside = self.base / 'keep'
        self.outside.mkdir()
        (self.outside / 'sentinel').write_text('preserve me')

    def tearDown(self):
        self.tmp.cleanup()

    def cleanup(self, candidate):
        return subprocess.run(['bash', '-c',
            'source "$REPO/scripts/common.sh"; OUTPUT_DIR="$CASE_OUTPUT"; safe_remove_work "$CASE_CANDIDATE"'],
            env={**os.environ, 'REPO': str(ROOT), 'CASE_OUTPUT': str(self.output),
                 'CASE_CANDIDATE': str(candidate)}, capture_output=True, text=True)

    def test_valid_work_removed_without_following_internal_symlink(self):
        work = self.output / '.v0.2-build.valid'
        work.mkdir()
        (work / '.vps-linux-work').touch()
        (work / 'external-link').symlink_to(self.outside, target_is_directory=True)
        self.assertEqual(self.cleanup(work).returncode, 0)
        self.assertFalse(work.exists())
        self.assertTrue((self.outside / 'sentinel').exists())

    def test_outside_path_rejected(self):
        (self.outside / '.vps-linux-work').touch()
        self.assertNotEqual(self.cleanup(self.outside).returncode, 0)
        self.assertTrue((self.outside / 'sentinel').exists())

    def test_symlink_work_rejected(self):
        (self.outside / '.vps-linux-work').touch()
        link = self.output / '.v0.2-build.link'
        link.symlink_to(self.outside, target_is_directory=True)
        self.assertNotEqual(self.cleanup(link).returncode, 0)
        self.assertTrue((self.outside / 'sentinel').exists())

    def test_unmarked_directory_rejected(self):
        work = self.output / '.v0.2-build.unmarked'
        work.mkdir()
        self.assertNotEqual(self.cleanup(work).returncode, 0)
        self.assertTrue(work.exists())


class FinalCandidateSelection(unittest.TestCase):
    def test_rejects_dev_and_dirty_candidates_and_selects_clean_final(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'VERSION').write_text('0.2\n')
            wrapper = root / 'tests/release-check.sh'
            wrapper.write_text((ROOT / 'tests/release-check.sh').read_text())
            smoke = root / 'tests/smoke-test.sh'
            smoke.write_text('#!/bin/bash\nprintf "%s\\n" "$@"\n')
            smoke.chmod(0o755)
            dev = root / 'output/vps-linux-v0.2-dev-20260101'
            dev.mkdir(parents=True)
            (dev / 'vps-linux-v0.2-dev.qcow2').touch()
            result = subprocess.run(['bash', str(wrapper)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            final = root / 'output/vps-linux-v0.2-20260101'
            final.mkdir()
            (final / 'vps-linux-v0.2.qcow2').touch()
            metadata = final / 'build.json'
            metadata.write_text(json.dumps({'version': '0.2', 'source_dirty': True}))
            result = subprocess.run(['bash', str(wrapper)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            metadata.write_text(json.dumps({'version': '0.2', 'source_dirty': False}))
            result = subprocess.run(['bash', str(wrapper)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--release-check', result.stdout)
            self.assertNotIn('0.2-dev', result.stdout)


class CommandLine(unittest.TestCase):
    def test_help_does_not_need_privilege(self):
        for script in ('build.sh', 'tests/smoke-test.sh'):
            with self.subTest(script=script):
                run = subprocess.run([str(ROOT / script), '--help'], capture_output=True, text=True)
                self.assertEqual(run.returncode, 0)
                self.assertIn('Usage:', run.stdout)

    def test_release_test_options_reject_malformed_arguments(self):
        for flags, message in ((['--bad'], 'Unknown option'), (['--accel'], 'Missing acceleration'), (['--accel', 'bad'], 'Invalid acceleration')):
            with self.subTest(flags=flags):
                run = subprocess.run([str(ROOT / 'tests/smoke-test.sh'), 'image.qcow2', *flags], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(message, run.stderr)

    def test_unknown_build_argument_rejected(self):
        run = subprocess.run([str(ROOT / 'build.sh'), '--disk=/dev/sda'], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('Unknown argument', run.stderr)


if __name__ == '__main__':
    unittest.main()

"""ABI gate unit tests independent of a compiler/package build."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('abi', ROOT / 'scripts/check-deb-abi.py')
ABI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ABI)


class PackagingABI(unittest.TestCase):
    def test_debian_13_or_older_floor_is_accepted(self):
        self.assertTrue(ABI.compatible('libc6 (>= 2.39), libgcc-s1 (>= 4.2)'))
        self.assertTrue(ABI.compatible('libc6 (>= 2.41)'))

    def test_missing_ambiguous_or_newer_floor_is_rejected(self):
        for deps in ['', 'libc6', 'libc6 (>= 2.42)', 'libc6 (>= 2.39), libc6 (>= 2.41)']:
            self.assertFalse(ABI.compatible(deps))

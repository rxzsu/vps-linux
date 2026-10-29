#!/usr/bin/env python3
"""Inspect and execute extracted package, without installing or requiring root."""
import pathlib
import subprocess
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / 'Cargo.toml').read_text())['package']['version']
PACKAGE = ROOT / 'dist' / f'vpsctl_{VERSION}_amd64.deb'


class DebianPackage(unittest.TestCase):
    def test_metadata_and_extracted_binary(self):
        version = subprocess.check_output(['dpkg-deb', '-f', str(PACKAGE), 'Version'], text=True).strip()
        self.assertEqual(version, VERSION)
        dependencies = subprocess.check_output(['dpkg-deb', '-f', str(PACKAGE), 'Depends'], text=True)
        self.assertIn('libc6 (>=', dependencies)
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(['dpkg-deb', '-R', str(PACKAGE), directory], check=True)
            root = pathlib.Path(directory)
            control = root / 'DEBIAN'
            self.assertEqual({p.name for p in control.iterdir()}, {'control'})
            # There must be no maintainer scripts, service units or config files.
            self.assertFalse((root / 'etc').exists())
            self.assertFalse((root / 'usr/lib/systemd').exists())
            binary = root / 'usr/bin/vpsctl'
            self.assertEqual(subprocess.check_output([str(binary), '--version'], text=True).strip(), f'vpsctl {VERSION}')
            self.assertEqual(binary.stat().st_mode & 0o7777, 0o755)


    def test_man_page_and_shell_completions(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(['dpkg-deb', '-R', str(PACKAGE), directory], check=True)
            root = pathlib.Path(directory)
            for name in ('usr/share/man/man1/vpsctl.1.gz',
                         'usr/share/bash-completion/completions/vpsctl',
                         'usr/share/zsh/vendor-completions/_vpsctl'):
                self.assertTrue((root / name).is_file(), f'missing {name}')


if __name__ == '__main__':
    unittest.main()

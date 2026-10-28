"""Cross-check security/provisioning policy and packaged project configuration."""
import configparser
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class Policy(unittest.TestCase):
    def test_release_version(self):
        self.assertEqual((ROOT / 'VERSION').read_text().strip(), '0.3-dev')

    def test_cloud_provisioning_policy(self):
        config = yaml.safe_load((ROOT / 'configs/cloud-init/99-vps-linux.cfg').read_text())
        self.assertIs(config['ssh_pwauth'], False)
        self.assertIs(config['ssh_deletekeys'], True)
        self.assertIs(config['disable_root'], True)
        self.assertEqual(config['datasource_list'], ['NoCloud'])
        self.assertEqual(config['users'], ['default'])
        user = config['system_info']['default_user']
        self.assertEqual(user['name'], 'debian')
        self.assertIs(user['lock_passwd'], True)
        self.assertNotIn('passwd', user)
        self.assertEqual(config['ssh_genkeytypes'], ['ed25519', 'ecdsa'])
        self.assertEqual(config['growpart']['mode'], 'auto')
        self.assertIs(config['resize_rootfs'], True)

    def test_key_fixture_is_public_placeholder_only(self):
        example = yaml.safe_load((ROOT / 'tests/cloud-init/user-data.example').read_text())
        self.assertEqual(example['users'], ['default'])
        self.assertEqual(example['ssh_authorized_keys'], ['ssh-ed25519 REPLACE_WITH_YOUR_PUBLIC_KEY'])

    def test_package_manifest_has_unique_valid_names(self):
        packages = [line for line in (ROOT / 'packages/base.txt').read_text().splitlines()
                    if line and not line.startswith('#')]
        self.assertEqual(len(packages), len(set(packages)))
        for name in packages:
            self.assertRegex(name, r'^[a-z0-9][a-z0-9+.-]+$')
        self.assertTrue({'docker-cli', 'docker.io', 'docker-compose', 'cloud-init',
                         'linux-image-amd64', 'grub-efi-amd64-bin',
                         'qemu-guest-agent', 'unattended-upgrades'} <= set(packages))

    def test_zram_size_and_priority(self):
        config = configparser.ConfigParser()
        config.read(ROOT / 'configs/zram/zram-generator.conf')
        self.assertEqual(config['zram0']['zram-size'], '1024')
        self.assertEqual(config['zram0']['compression-algorithm'], 'lz4')
        self.assertEqual(config['zram0']['swap-priority'], '100')

    def test_docker_configuration(self):
        config = json.loads((ROOT / 'configs/docker/daemon.json').read_text())
        self.assertEqual(config['storage-driver'], 'overlay2')
        self.assertIs(config['live-restore'], True)
        self.assertEqual(config['log-driver'], 'json-file')
        self.assertEqual(config['log-opts'], {'max-size': '10m', 'max-file': '3'})
        self.assertNotIn('hosts', config)  # Do not expose unauthenticated TCP Docker API.

    def test_journald_limits(self):
        settings = {}
        for line in (ROOT / 'configs/systemd/journald.conf.d/99-vps-linux.conf').read_text().splitlines():
            if line and not line.startswith(('#', '[')):
                key, value = line.split('=', 1)
                settings[key] = value
        self.assertEqual(settings['SystemMaxUse'], '200M')
        self.assertEqual(settings['RuntimeMaxUse'], '50M')
        self.assertEqual(settings['SystemMaxFileSize'], '50M')

    def test_unattended_upgrade_policy(self):
        periodic = {}
        for line in (ROOT / 'configs/apt/20auto-upgrades').read_text().splitlines():
            if line:
                key, value = line.split(None, 1)
                periodic[key] = value.strip('";')
        self.assertEqual(periodic['APT::Periodic::Update-Package-Lists'], '1')
        self.assertEqual(periodic['APT::Periodic::Unattended-Upgrade'], '1')
        policy = (ROOT / 'configs/apt/52-vps-linux-unattended-upgrades').read_text()
        self.assertIn('"Debian:${distro_codename}-security"', policy)
        self.assertNotIn('-updates"', policy)
        self.assertIn('Unattended-Upgrade::Automatic-Reboot "false";', policy)
        self.assertIn('Unattended-Upgrade::Remove-Unused-Dependencies "false";', policy)

    def test_qemu_guest_agent_is_guarded(self):
        unit = (ROOT / 'configs/systemd/qemu-guest-agent.conf').read_text()
        self.assertIn('ConditionPathExists=/dev/virtio-ports/org.qemu.guest_agent.0', unit)
        configure = (ROOT / 'scripts/configure.sh').read_text()
        self.assertIn('qemu-guest-agent.service', configure)
        self.assertIn('apt-daily.timer', configure)
        self.assertIn('apt-daily-upgrade.timer', configure)

    def test_vendored_public_archive_keys(self):
        with tempfile.TemporaryDirectory() as home:
            run = subprocess.run(['gpg', '--no-options', '--batch', '--homedir', home,
                                  '--show-keys', '--with-colons',
                                  str(ROOT / 'configs/apt/debian-trixie.asc')],
                                 text=True, capture_output=True, check=True)
        primary = []
        need_fingerprint = False
        for line in run.stdout.splitlines():
            if line.startswith('pub:'):
                need_fingerprint = True
            elif line.startswith('fpr:') and need_fingerprint:
                primary.append(line.split(':')[9])
                need_fingerprint = False
        self.assertEqual(set(primary), {
            '04B54C3CDCA79751B16BC6B5225629DF75B188BD',
            '5E04A1E3223A19A20706E20F9904613D4CCE68C6',
            '41587F7DB8C774BCCF131416762F67A0B2C39DE4',
        })

    def test_workflow_yaml_parses(self):
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            config = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
            self.assertIn('jobs', config)
            self.assertIn('on', config)


if __name__ == '__main__':
    unittest.main()

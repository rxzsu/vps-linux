"""Check the guest boot gate before any functional assertions run."""
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class BootReadiness(unittest.TestCase):
    def run_gate(self, state, status):
        script = (ROOT / 'tests/verify-guest.sh').read_text().split('expected_hostname=$1', 1)[0]
        mocks = r'''
set -eu
systemctl() {
    if [[ $* == 'is-system-running --wait' ]]; then
        echo "$MOCK_STATE"
        return "$MOCK_STATUS"
    fi
    echo "diagnostics: $*" >&2
}
timeout() {
    [[ $1 == 180 && $2 == systemctl && $3 == is-system-running && $4 == --wait ]] || return 99
    shift
    "$@"
}
sudo() { echo "journal: $*" >&2; }
'''
        return subprocess.run(['bash', '-c', 'MOCK_STATE=$1; MOCK_STATUS=$2\n' + mocks + script,
                               'test', state, str(status)], capture_output=True, text=True)

    def test_waits_for_running_boot(self):
        result = self.run_gate('running', 0)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_failed_service_remains_failure_with_journal(self):
        result = self.run_gate('degraded', 1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('degraded', result.stderr)
        self.assertIn('journal:', result.stderr)

    def test_boot_deadline_remains_failure(self):
        result = self.run_gate('', 124)
        self.assertNotEqual(result.returncode, 0)

    def test_unexpected_state_is_rejected(self):
        result = self.run_gate('starting', 0)
        self.assertNotEqual(result.returncode, 0)

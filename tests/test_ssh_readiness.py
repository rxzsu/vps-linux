"""Exercise readiness retries without a VM or waiting for real SSH timeouts."""
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SSHReadinessTests(unittest.TestCase):
    def run_wait(self, statuses, budget=10, alive=True):
        script = r'''
source tests/ssh-readiness.sh
statuses=($1)
calls=0
kill() { [[ $2 != dead ]]; }
timeout() {
    [[ ${*: -1} == 'cloud-init status --wait --long' ]] || return 99
    local status=${statuses[$calls]:-99}
    calls=$((calls + 1))
    return "$status"
}
sleep() { SECONDS=$((SECONDS + 2)); }
status=0
wait_for_cloud_init "$3" "$2" ssh fake-host || status=$?
printf '%s %s\n' "$status" "$calls"
'''
        result = subprocess.run(['bash', '-euc', script, 'test', statuses, str(budget),
                                 'alive' if alive else 'dead'], cwd=ROOT,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_recovers_from_reset_after_first_ssh_success(self):
        self.assertEqual(self.run_wait('255 255 0'), '0 3')

    def test_cloud_init_failure_is_not_retried(self):
        self.assertEqual(self.run_wait('1 0'), '1 1')
        self.assertEqual(self.run_wait('2 0'), '2 1')

    def test_timeout_is_not_retried(self):
        self.assertEqual(self.run_wait('124 0'), '124 1')

    def test_repeated_disconnects_have_a_deadline(self):
        self.assertEqual(self.run_wait('255 255 0', budget=3), '124 2')

    def test_dead_qemu_fails_without_ssh(self):
        self.assertEqual(self.run_wait('0', alive=False), '1 0')

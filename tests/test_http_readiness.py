"""Run the online guest script with deterministic Docker/HTTP startup failures."""
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class HTTPReadiness(unittest.TestCase):
    def run_guest(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, HTTP_TEST_DIR=directory, HTTP_TEST_MODE=mode)
            result = subprocess.run(['bash', '-c', r'''
cat() { echo 0.3-dev; }
timedatectl() { echo yes; }
sudo() { echo "docker: $*" >&2; }
systemctl() { :; }
sleep() { SECONDS=$((SECONDS + 90)); }
curl() {
    if [[ ! -f $HTTP_TEST_DIR/attempt ]]; then
        touch "$HTTP_TEST_DIR/attempt"
        case $HTTP_TEST_MODE in
            reset) return 56 ;;
            refused) return 7 ;;
            wrong-body) echo 'not nginx'; return 0 ;;
        esac
    fi
    if [[ $HTTP_TEST_MODE == permanent ]]; then return 56; fi
    echo 'Welcome to nginx!'
}
# Allow a second attempt while keeping permanent failures bounded and fast.
if [[ $HTTP_TEST_MODE != permanent ]]; then
    sleep() { :; }
fi
source tests/verify-online-guest.sh
'''], cwd=ROOT, env=env, capture_output=True, text=True, timeout=5)
            return result

    def test_reset_then_success(self):
        result = self.run_guest('reset')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('HTTP nginx readiness: passed', result.stdout)

    def test_refusal_then_success(self):
        result = self.run_guest('refused')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wrong_body_requires_another_request(self):
        result = self.run_guest('wrong-body')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('HTTP nginx readiness: passed', result.stdout)

    def test_permanent_failure_keeps_release_blocked_and_prints_diagnostics(self):
        result = self.run_guest('permanent')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HTTP nginx readiness timed out', result.stderr)
        self.assertIn('docker inspect vps-linux-release-http', result.stderr)
        self.assertIn('docker logs --tail 50', result.stderr)
        self.assertNotIn('HTTP workload: passed', result.stdout)

#!/usr/bin/env bash
# One local command: static/integrity tests, signed build, extended VM tests.
# The ephemeral minisign key authenticates this test run, not a public release.
set -Eeuo pipefail
umask 077
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
[[ $# == 0 ]] || { echo 'Usage: ./tests/v0.3-check.sh' >&2; exit 1; }
[[ $(cat "$PROJECT_DIR/VERSION") == 0.3-dev ]] || { echo 'This test command requires VERSION=0.3-dev' >&2; exit 1; }
for tool in minisign shellcheck qemu-img sudo; do
    command -v "$tool" >/dev/null || { echo "Missing $tool. See docs/testing.md for dependencies." >&2; exit 1; }
done
"$PROJECT_DIR/tests/static-checks.sh"
sudo "$PROJECT_DIR/build.sh" --check
work=$(mktemp -d /tmp/vps-linux-v03-signing.XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
minisign -G -W -p "$work/test.pub" -s "$work/test.key" > "$work/keygen.log" 2>&1
mkdir -p "$PROJECT_DIR/output"
# Exclusive run marker selects this invocation's completed bundle only.
touch "$work/start"
sudo env VPS_LINUX_SIGNING_KEY="$work/test.key" "$PROJECT_DIR/build.sh"
image=$(python3 - "$PROJECT_DIR" "$work/start" <<'PY'
import pathlib, sys
root, marker = map(pathlib.Path, sys.argv[1:])
images = [p for p in (root / 'output').glob('vps-linux-v0.3-dev-*/vps-linux-v0.3-dev.qcow2')
          if p.stat().st_mtime_ns >= marker.stat().st_mtime_ns]
if len(images) != 1:
    sys.exit('Expected exactly one new completed candidate; concurrent builds are unsupported by this wrapper')
print(images[0])
PY
)
bundle=$(dirname "$image")
"$PROJECT_DIR/scripts/verify-release.sh" "$bundle" --minisign-pubkey "$work/test.pub"
"$PROJECT_DIR/tests/smoke-test.sh" "$image" --release-check
# Retain the public test key outside the immutable bundle; never retain the private key.
report="$PROJECT_DIR/output/v03-test-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -m700 "$report"
cp "$work/test.pub" "$report/minisign-test.pub"
python3 - "$bundle" "$report" <<'PY'
import datetime, json, pathlib, sys
bundle, report = map(pathlib.Path, sys.argv[1:])
metadata = json.loads((bundle / 'build.json').read_text())
result = {'version': metadata['version'], 'source_commit': metadata['source_commit'],
          'source_dirty': metadata['source_dirty'], 'image_sha256': metadata['image_sha256'],
          'bundle': str(bundle), 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'result': 'passed', 'local_test_signature': 'verified',
          'test_key_is_release_trust_root': False,
          'checks': ['integrity/signature regressions', 'two UEFI/NoCloud boots', 'guest-ping',
                     'effective security-only APT policy', 'container log rotation',
                     '8-to-10-GiB partition/filesystem growth and GPT relocation',
                     'online Docker/HTTP/NTP', 'reboot and persistent identities'],
          'keyless_cosign': 'not_run; requires the GitHub Actions OIDC workflow'}
(report / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
PY
printf '\nPASS: v0.3 build, signature and VM acceptance completed. Report: %s/acceptance.json\n' "$report"

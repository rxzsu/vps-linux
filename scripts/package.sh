#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_work
bundle="$VPS_LINUX_WORK/release"
image="$bundle/vps-linux-v0.2-dev.qcow2"
qemu-img convert -f raw -O qcow2 -o compat=1.1,lazy_refcounts=off "$VPS_LINUX_WORK/disk.raw" "$image"
qemu-img check -f qcow2 "$image"
qemu-img info --output=json --force-share "$image" | python3 "$PROJECT_DIR/scripts/check-image.py"
(cd "$bundle" && sha256sum vps-linux-v0.2-dev.qcow2 > vps-linux-v0.2-dev.qcow2.sha256 && sha256sum -c vps-linux-v0.2-dev.qcow2.sha256)
python3 - "$bundle" "$PROJECT_DIR" <<'PY'
import datetime, hashlib, json, pathlib, subprocess, sys
bundle, source = map(pathlib.Path, sys.argv[1:])
def git(*args):
    return subprocess.check_output(['git', '-c', f'safe.directory={source}', '-C', str(source), *args], text=True).strip()
metadata = {
    'version': '0.2-dev', 'suite': 'trixie', 'architecture': 'amd64',
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_commit': git('rev-parse', 'HEAD'),
    'source_dirty': bool(git('status', '--porcelain', '--untracked-files=normal')),
    'mirrors': ['https://deb.debian.org/debian', 'https://security.debian.org/debian-security'],
    'package_manifest_sha256': hashlib.sha256((bundle / 'packages.tsv').read_bytes()).hexdigest(),
    'image_sha256': (bundle / 'vps-linux-v0.2-dev.qcow2.sha256').read_text().split()[0],
    'virtual_size_bytes': 8 * 1024**3,
    'byte_reproducibility_verified': False, 'boot_smoke_test': 'not_run',
    'secure_boot_supported': False,
}
(bundle / 'build.json').write_text(json.dumps(metadata, indent=2) + '\n')
PY
chmod 444 "$bundle"/*

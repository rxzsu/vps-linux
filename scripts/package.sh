#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_work
bundle="$VPS_LINUX_WORK/release"
image="$bundle/vps-linux-v${VPS_LINUX_VERSION}.qcow2"
qemu-img convert -f raw -O qcow2 -o compat=1.1,lazy_refcounts=off "$VPS_LINUX_WORK/disk.raw" "$image"
qemu-img check -f qcow2 "$image"
qemu-img info --output=json --force-share "$image" | python3 "$PROJECT_DIR/scripts/check-image.py"
(cd "$bundle" && sha256sum "vps-linux-v${VPS_LINUX_VERSION}.qcow2" > "vps-linux-v${VPS_LINUX_VERSION}.qcow2.sha256" && sha256sum -c "vps-linux-v${VPS_LINUX_VERSION}.qcow2.sha256")
python3 - "$bundle" "$PROJECT_DIR" "$VPS_LINUX_VERSION" <<'PY'
import datetime, hashlib, json, os, pathlib, subprocess, sys
bundle, source = map(pathlib.Path, sys.argv[1:3])
version = sys.argv[3]
def git(*args):
    return subprocess.check_output(['git', '-c', f'safe.directory={source}', '-C', str(source), *args], text=True).strip()
commit = git('rev-parse', 'HEAD')
dirty = bool(git('status', '--porcelain', '--untracked-files=normal'))
if commit != os.environ['VPS_LINUX_SOURCE_COMMIT'] or (not version.endswith('-dev') and dirty):
    sys.exit('Source changed during build; refusing to package a stable candidate')
vpsctl = json.loads((pathlib.Path(os.environ['VPS_LINUX_WORK']) / 'vpsctl.json').read_text())
metadata = {
    'vpsctl': vpsctl,
    'version': version, 'suite': 'trixie', 'architecture': 'amd64',
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_commit': commit,
    'source_dirty': dirty,
    'mirrors': ['https://deb.debian.org/debian', 'https://security.debian.org/debian-security'],
    'package_manifest_sha256': hashlib.sha256((bundle / 'packages.tsv').read_bytes()).hexdigest(),
    'image_sha256': (bundle / f'vps-linux-v{version}.qcow2.sha256').read_text().split()[0],
    'virtual_size_bytes': 8 * 1024**3,
    'sbom': 'sbom.spdx.json',
    'artifact_checksums': 'SHA256SUMS',
    'byte_reproducibility_verified': False, 'boot_smoke_test': 'not_run',
    'secure_boot_supported': False,
}
(bundle / 'build.json').write_text(json.dumps(metadata, indent=2) + '\n')
PY
vpsctl_file=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["vpsctl"]["package_file"])' "$bundle/build.json")
cp "$VPS_LINUX_WORK/vpsctl.deb" "$bundle/$vpsctl_file"
created=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["created_utc"])' "$bundle/build.json")
python3 "$PROJECT_DIR/scripts/generate-sbom.py" \
    "$bundle/packages.tsv" "$bundle/sbom.spdx.json" \
    --version "$VPS_LINUX_VERSION" --commit "$VPS_LINUX_SOURCE_COMMIT" --created "$created"
(cd "$bundle" && sha256sum \
    "vps-linux-v${VPS_LINUX_VERSION}.qcow2" \
    "vps-linux-v${VPS_LINUX_VERSION}.qcow2.sha256" \
    packages.tsv build.json sbom.spdx.json "$vpsctl_file" > SHA256SUMS)
# Optional local signing. CI uses keyless cosign on SHA256SUMS instead, so no
# private key ever needs to exist in this repository or on a runner.
if [[ -n ${VPS_LINUX_SIGNING_KEY:-} ]]; then
    command -v minisign >/dev/null || die 'VPS_LINUX_SIGNING_KEY is set but minisign is missing.'
    [[ -f $VPS_LINUX_SIGNING_KEY ]] || die "Signing key not found: $VPS_LINUX_SIGNING_KEY"
    minisign -Sm "$bundle/SHA256SUMS" -s "$VPS_LINUX_SIGNING_KEY" \
        -t "vps-linux v${VPS_LINUX_VERSION} ${VPS_LINUX_SOURCE_COMMIT}"
    log 'Signed SHA256SUMS with the local minisign key.'
fi
chmod 444 "$bundle"/*

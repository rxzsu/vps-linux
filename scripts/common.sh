#!/usr/bin/env bash
# Shared host helpers. No mount, loop or NBD operations are performed on the host.
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
OUTPUT_DIR="$PROJECT_DIR/output"
log() { printf '[vps-linux] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }
ensure_output() {
    [[ ! -L $OUTPUT_DIR ]] || die 'output/ must not be a symbolic link.'
    mkdir -p -- "$OUTPUT_DIR"
    [[ $(realpath -e -- "$OUTPUT_DIR") == "$OUTPUT_DIR" ]] || die 'Unsafe output path.'
}
require_work() {
    [[ -n ${VPS_LINUX_WORK:-} && ! -L $VPS_LINUX_WORK ]] || die 'Missing safe build workspace; run build.sh.'
    [[ $VPS_LINUX_WORK == "$OUTPUT_DIR"/.v0.2-build.* && -f $VPS_LINUX_WORK/.vps-linux-work ]] || die 'Invalid build workspace marker.'
    [[ $(realpath -e -- "$VPS_LINUX_WORK") == "$VPS_LINUX_WORK" ]] || die 'Build workspace resolves outside output/.'
}
safe_remove_work() {
    local candidate=$1
    [[ -d $candidate && ! -L $candidate && $candidate == "$OUTPUT_DIR"/.v0.2-build.* && -f $candidate/.vps-linux-work ]] || { log 'Refusing unsafe cleanup path.'; return 1; }
    [[ $(realpath -e -- "$candidate") == "$candidate" ]] || return 1
    # Refuse cleanup if a mount remains, including same-filesystem bind mounts.
    python3 - "$candidate" <<'PY'
import re, sys
from pathlib import Path
root = sys.argv[1]
for line in Path('/proc/self/mountinfo').read_text().splitlines():
    target = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), line.split()[4])
    if target == root or target.startswith(root + '/'):
        sys.exit('Refusing cleanup: mount remains at ' + target)
PY
    local status=$?
    (( status == 0 )) || return "$status"
    rm -rf --one-file-system -- "$candidate"
}
preflight_build() {
    local failed=0 tool available space_root="$PROJECT_DIR"
    [[ $PROJECT_DIR =~ ^/[a-zA-Z0-9._/-]+$ ]] || { log "Checkout path must contain only letters, digits, dots, underscores, slashes and hyphens."; failed=1; }
    [[ $(uname -m) == x86_64 ]] || { log 'Only native x86_64 hosts are supported.'; failed=1; }
    [[ $EUID == 0 ]] || { log 'Build requires root: sudo ./build.sh (mmdebstrap chroot in an isolated namespace).'; failed=1; }
    # shellcheck disable=SC1091
    source /etc/os-release
    if ! { [[ $ID == debian && ${VERSION_ID%%.*} == 13 ]] || [[ ${UBUNTU_CODENAME:-${VERSION_CODENAME:-}} == noble ]]; }; then
        log 'Supported hosts: Debian 13 or Ubuntu 24.04 / Zorin based on Noble.'; failed=1
    fi
    for tool in mmdebstrap unshare guestfish virt-customize qemu-img python3 gpg flock realpath git stat df setsid timeout tail systemctl; do
        command -v "$tool" >/dev/null || { log "Missing tool: $tool (see docs/building.md)"; failed=1; }
    done
    [[ ! -L $OUTPUT_DIR ]] || { log 'output/ must not be a symbolic link.'; failed=1; }
    if ! python3 - "$PROJECT_DIR" <<'PY_CONFIG'
import configparser, json, pathlib, re, sys
try:
    import yaml
    root = pathlib.Path(sys.argv[1])
    config = yaml.safe_load((root / 'configs/cloud-init/99-vps-linux.cfg').read_text())
    if not isinstance(config, dict):
        raise ValueError('cloud-init system config must be a mapping')
    json.loads((root / 'configs/docker/daemon.json').read_text())
    for filename in ('configs/zram/zram-generator.conf', 'configs/network/10-vps-linux.network'):
        ini = configparser.ConfigParser(interpolation=None)
        ini.read_string((root / filename).read_text())
    for name in (root / 'packages/base.txt').read_text().splitlines():
        if name and not name.startswith('#') and not re.fullmatch(r'[a-z0-9][a-z0-9+.-]+', name):
            raise ValueError('invalid package name: ' + name)
except Exception as error:
    sys.exit('Invalid build configuration / missing PyYAML: ' + str(error))
PY_CONFIG
    then
        failed=1
    fi
    if [[ -d $OUTPUT_DIR && ! -L $OUTPUT_DIR ]]; then space_root=$OUTPUT_DIR; fi
    available=$(df -Pk -- "$space_root" | awk 'END {print $4}')
    (( available >= 20 * 1024 * 1024 )) || { log 'At least 20 GiB free disk space is required.'; failed=1; }
    if [[ $EUID == 0 ]] && ! unshare --mount --pid --fork --kill-child --mount-proc --propagation private true; then
        log 'Private mount/PID namespaces are unavailable; use a full VM/host, not a restricted container.'; failed=1
    fi
    (( failed == 0 )) || die 'Host preflight failed. No image or disk was touched.'
}

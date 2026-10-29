#!/usr/bin/env bash
# Build a versioned candidate; never modify an existing release.
set -Eeuo pipefail
umask 022
set +m  # Each stage gets a separate process group via setsid.
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=scripts/common.sh
source "$PROJECT_DIR/scripts/common.sh"
case ${1:-} in
    --help|-h) printf 'Usage: sudo ./build.sh [--check]\nBuild Debian Trixie amd64 v%s under output/. Existing artifacts are never overwritten.\n' "$VPS_LINUX_VERSION"; exit 0 ;;
    --check|'') ;;
    *) die 'Unknown argument. Use ./build.sh --help.' ;;
esac
[[ $# -le 1 ]] || die 'Too many arguments.'
# Stable candidates must bind to committed sources, including helper files.
if [[ $VPS_LINUX_VERSION != *-dev ]] && [[ -n $(git -c safe.directory="$PROJECT_DIR" -C "$PROJECT_DIR" status --porcelain --untracked-files=normal) ]]; then
    die 'Stable candidate requires a clean checkout. Preserve/commit or stash local edits before building.'
fi
preflight_build
[[ ${1:-} != --check ]] || { log 'Host preflight passed; no image was built.'; exit 0; }
VPS_LINUX_SOURCE_COMMIT=$(git -c safe.directory="$PROJECT_DIR" -C "$PROJECT_DIR" rev-parse HEAD)
export VPS_LINUX_SOURCE_COMMIT
ensure_output
exec 9>"$OUTPUT_DIR/.build.lock"
flock -n 9 || die 'Another build holds output/.build.lock.'
VPS_LINUX_WORK=$(mktemp -d "$OUTPUT_DIR/.vps-linux-build.XXXXXXXX")
export VPS_LINUX_WORK
: > "$VPS_LINUX_WORK/.vps-linux-work"
active_pid=''
cleanup() {
    local status=$?
    trap - EXIT
    if [[ -n $active_pid ]]; then
        kill -TERM -- "-$active_pid" 2>/dev/null || kill -TERM "$active_pid" 2>/dev/null || true
        timeout 10 tail --pid="$active_pid" -f /dev/null 2>/dev/null || true
        kill -KILL -- "-$active_pid" 2>/dev/null || true
        wait "$active_pid" 2>/dev/null || true
    fi
    safe_remove_work "$VPS_LINUX_WORK" || status=1
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
run_stage() {
    setsid --wait "$@" &
    active_pid=$!
    wait "$active_pid"
    active_pid=''
}
install -m444 -- "$VPS_LINUX_VPSCTL_DEB" "$VPS_LINUX_WORK/vpsctl.deb"
python3 "$PROJECT_DIR/scripts/vpsctl_package.py" --source "$PROJECT_DIR" --package "$VPS_LINUX_WORK/vpsctl.deb" --json > "$VPS_LINUX_WORK/vpsctl.json"
export VPS_LINUX_VPSCTL_DEB="$VPS_LINUX_WORK/vpsctl.deb"
mkdir -m 700 "$VPS_LINUX_WORK/release" "$VPS_LINUX_WORK/gnupg"
export GNUPGHOME="$VPS_LINUX_WORK/gnupg"
export TMPDIR="$VPS_LINUX_WORK"
export LIBGUESTFS_BACKEND=direct
export VPS_LINUX_SOURCE_DIR="$PROJECT_DIR"
# Anchor timestamps to the source commit; mmdebstrap and packaging tools honor
# this where possible. Full byte-for-byte reproducibility is a separate milestone.
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git -c safe.directory="$PROJECT_DIR" -C "$PROJECT_DIR" log -1 --format=%ct HEAD)}
[[ $SOURCE_DATE_EPOCH =~ ^[0-9]+$ ]] || die 'Invalid SOURCE_DATE_EPOCH from git history.'
export DEBIAN_FRONTEND=noninteractive
BUILD_ID="vps-linux-v${VPS_LINUX_VERSION}-$(date -u +%Y%m%dT%H%M%SZ)-${VPS_LINUX_SOURCE_COMMIT:0:12}"
[[ ! -e $OUTPUT_DIR/$BUILD_ID ]] || die 'Build identifier already exists; retry after one second.'
log 'A/B: bootstrap Debian in a private mount/PID namespace'
run_stage "$PROJECT_DIR/scripts/bootstrap.sh"
log 'C: create GPT/EFI/ext4 disk inside the libguestfs appliance'
run_stage "$PROJECT_DIR/scripts/create-image.sh"
log 'E/F: install removable UEFI bootloader and clean guest state'
run_stage "$PROJECT_DIR/scripts/install-bootloader.sh"
log 'G: package and verify versioned candidate'
run_stage "$PROJECT_DIR/scripts/package.sh"
# Directory rename publishes the complete bundle on the same filesystem.
chmod 755 "$VPS_LINUX_WORK/release"
mv -T -- "$VPS_LINUX_WORK/release" "$OUTPUT_DIR/$BUILD_ID"
printf '\nBuild completed (boot test still required):\n%s\n' "$OUTPUT_DIR/$BUILD_ID/vps-linux-v${VPS_LINUX_VERSION}.qcow2"
printf 'Run: ./tests/smoke-test.sh %q\n' "$OUTPUT_DIR/$BUILD_ID/vps-linux-v${VPS_LINUX_VERSION}.qcow2"

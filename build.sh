#!/usr/bin/env bash
# Build a DEVELOPMENT image, never modify an existing release.
set -Eeuo pipefail
umask 022
set +m  # Each stage gets a separate process group via setsid.
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=scripts/common.sh
source "$PROJECT_DIR/scripts/common.sh"
case ${1:-} in
    --help|-h) printf 'Usage: sudo ./build.sh [--check]\nBuild Debian Trixie amd64 v0.2-dev under output/. Existing artifacts are never overwritten.\n'; exit 0 ;;
    --check|'') ;;
    *) die 'Unknown argument. Use ./build.sh --help.' ;;
esac
[[ $# -le 1 ]] || die 'Too many arguments.'
preflight_build
[[ ${1:-} != --check ]] || { log 'Host preflight passed; no image was built.'; exit 0; }
ensure_output
exec 9>"$OUTPUT_DIR/.build.lock"
flock -n 9 || die 'Another build holds output/.build.lock.'
VPS_LINUX_WORK=$(mktemp -d "$OUTPUT_DIR/.v0.2-build.XXXXXXXX")
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
mkdir -m 700 "$VPS_LINUX_WORK/release" "$VPS_LINUX_WORK/gnupg"
export GNUPGHOME="$VPS_LINUX_WORK/gnupg"
export TMPDIR="$VPS_LINUX_WORK"
export LIBGUESTFS_BACKEND=direct
export VPS_LINUX_SOURCE_DIR="$PROJECT_DIR"
export DEBIAN_FRONTEND=noninteractive
BUILD_ID="vps-linux-v0.2-dev-$(date -u +%Y%m%dT%H%M%SZ)-$(git -c safe.directory="$PROJECT_DIR" -C "$PROJECT_DIR" rev-parse --short=12 HEAD)"
[[ ! -e $OUTPUT_DIR/$BUILD_ID ]] || die 'Build identifier already exists; retry after one second.'
log 'A/B: bootstrap Debian in a private mount/PID namespace'
run_stage "$PROJECT_DIR/scripts/bootstrap.sh"
log 'C: create GPT/EFI/ext4 disk inside the libguestfs appliance'
run_stage "$PROJECT_DIR/scripts/create-image.sh"
log 'E/F: install removable UEFI bootloader and clean guest state'
run_stage "$PROJECT_DIR/scripts/install-bootloader.sh"
log 'G: package and verify development artifact'
run_stage "$PROJECT_DIR/scripts/package.sh"
# Directory rename publishes the complete bundle on the same filesystem.
chmod 755 "$VPS_LINUX_WORK/release"
mv -T -- "$VPS_LINUX_WORK/release" "$OUTPUT_DIR/$BUILD_ID"
printf '\nBuild completed (boot test still required):\n%s\n' "$OUTPUT_DIR/$BUILD_ID/vps-linux-v0.2-dev.qcow2"
printf 'Run: ./tests/smoke-test.sh %q\n' "$OUTPUT_DIR/$BUILD_ID/vps-linux-v0.2-dev.qcow2"

#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_work
mapfile -t packages < <(sed -e '/^[[:space:]]*#/d' -e '/^[[:space:]]*$/d' "$PROJECT_DIR/packages/base.txt")
for package in "${packages[@]}"; do
    [[ $package =~ ^[a-z0-9][a-z0-9+.-]+$ ]] || die "Invalid package name: $package"
done
include=$(IFS=,; printf '%s' "${packages[*]}")
gpg --no-options --batch --dearmor --output "$VPS_LINUX_WORK/debian-trixie.gpg" "$PROJECT_DIR/configs/apt/debian-trixie.asc"
# All bootstrap mounts live in this namespace. Killing its PID 1 also kills
# descendants; the host mount table is never modified.
# Hook variables expand in mmdebstrap, not in this shell.
# shellcheck disable=SC2016
unshare --mount --pid --fork --kill-child --mount-proc --propagation private \
    mmdebstrap --mode=root --variant=minbase --architectures=amd64 --format=tar \
    --keyring="$VPS_LINUX_WORK/debian-trixie.gpg" \
    --include="$include" \
    --aptopt='APT::Install-Recommends "false"' \
    --customize-hook='exec "$VPS_LINUX_SOURCE_DIR/scripts/configure.sh" "$1"' \
    trixie "$VPS_LINUX_WORK/rootfs.tar" \
    'deb https://deb.debian.org/debian trixie main' \
    'deb https://deb.debian.org/debian trixie-updates main' \
    'deb https://security.debian.org/debian-security trixie-security main'

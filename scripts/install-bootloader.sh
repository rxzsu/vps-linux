#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_work
# libguestfs mounts the guest according to its fstab in a dedicated appliance.
# GRUB installs fallback BOOTX64.EFI, without host or guest NVRAM dependencies.
virt-customize --format raw -a "$VPS_LINUX_WORK/disk.raw" --no-network \
    --run-command 'update-initramfs -u -k all' \
    --run-command 'grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=VPSLinux --removable --no-nvram --recheck' \
    --run-command 'update-grub' \
    --run-command 'test -s /boot/efi/EFI/BOOT/BOOTX64.EFI && test -s /boot/grub/grub.cfg' \
    --upload "$PROJECT_DIR/scripts/cleanup-guest.sh:/root/vps-linux-cleanup.sh" \
    --run-command 'bash /root/vps-linux-cleanup.sh' \
    --run-command 'rm -f /root/vps-linux-cleanup.sh'
# Inspect the sealed guest before converting it. Keys must regenerate on boot.
# Command substitution must happen inside the guest.
# shellcheck disable=SC2016
guestfish --ro --format=raw -a "$VPS_LINUX_WORK/disk.raw" -i sh \
    'test -s /boot/efi/EFI/BOOT/BOOTX64.EFI && test ! -s /etc/machine-id && test ! -e /usr/share/vps-linux/.build-in-progress && test -z "$(find /etc/ssh -name "ssh_host_*" -print -quit)" && test -z "$(find /home -mindepth 1 -print -quit)"'

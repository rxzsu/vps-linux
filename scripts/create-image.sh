#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_work
[[ -f $VPS_LINUX_WORK/rootfs.tar ]] || die 'Missing bootstrapped filesystem.'
qemu-img create -f raw "$VPS_LINUX_WORK/disk.raw" 8G
# /dev/sda here exists ONLY inside the libguestfs VM. The sole attached drive is
# our newly-created regular file. Never run these commands against the host.
guestfish --rw --format=raw -a "$VPS_LINUX_WORK/disk.raw" <<EOF_GUEST
run
part-init /dev/sda gpt
part-add /dev/sda p 2048 1050623
part-add /dev/sda p 1050624 -2049
part-set-gpt-type /dev/sda 1 C12A7328-F81F-11D2-BA4B-00A0C93EC93B
mkfs vfat /dev/sda1
set-label /dev/sda1 VPS_EFI
mkfs ext4 /dev/sda2
set-label /dev/sda2 VPS_ROOT
mount /dev/sda2 /
tar-in "$VPS_LINUX_WORK/rootfs.tar" / xattrs:true acls:true
mkdir-p /boot/efi
mount /dev/sda1 /boot/efi
sync
umount-all
shutdown
EOF_GUEST

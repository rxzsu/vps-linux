#!/usr/bin/env bash
# mmdebstrap customize hook, invoked after package installation.
set -Eeuo pipefail
# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"
require_work
[[ $# == 1 ]] || die 'configure.sh is an internal bootstrap hook.'
root=$(realpath -e -- "$1")
[[ $root == "$VPS_LINUX_WORK"/* && $root != / && -f $root/etc/debian_version ]] || die 'Unsafe bootstrap root.'
# Install the validated snapshot into dpkg's database, not just a loose binary.
install -m644 "$VPS_LINUX_VPSCTL_DEB" "$root/tmp/vpsctl.deb"
chroot "$root" dpkg -i /tmp/vpsctl.deb
rm -f "$root/tmp/vpsctl.deb"
chroot "$root" vpsctl --version
chroot "$root" vpsctl status --json >/dev/null
install -Dm644 "$PROJECT_DIR/configs/cloud-init/99-vps-linux.cfg" "$root/etc/cloud/cloud.cfg.d/99-vps-linux.cfg"
install -Dm644 "$PROJECT_DIR/configs/ssh/00-vps-linux.conf" "$root/etc/ssh/sshd_config.d/00-vps-linux.conf"
install -Dm644 "$PROJECT_DIR/configs/network/10-vps-linux.network" "$root/etc/systemd/network/10-vps-linux.network"
install -Dm644 "$PROJECT_DIR/configs/zram/zram-generator.conf" "$root/etc/systemd/zram-generator.conf"
install -Dm644 "$PROJECT_DIR/configs/systemd/grub-defaults.cfg" "$root/etc/default/grub.d/99-vps-linux.cfg"
install -Dm644 "$PROJECT_DIR/configs/docker/daemon.json" "$root/etc/docker/daemon.json"
install -Dm644 "$PROJECT_DIR/configs/sysctl/90-vps-linux.conf" "$root/etc/sysctl.d/90-vps-linux.conf"
install -Dm644 "$PROJECT_DIR/configs/systemd/coredump.conf.d/99-vps-linux.conf" "$root/etc/systemd/coredump.conf.d/99-vps-linux.conf"
install -Dm644 "$PROJECT_DIR/configs/systemd/system.conf.d/99-vps-linux.conf" "$root/etc/systemd/system.conf.d/99-vps-linux.conf"
install -Dm755 "$PROJECT_DIR/configs/motd/10-vps-linux" "$root/etc/update-motd.d/10-vps-linux"
install -Dm644 "$PROJECT_DIR/configs/systemd/journald.conf.d/99-vps-linux.conf" "$root/etc/systemd/journald.conf.d/99-vps-linux.conf"
install -Dm644 "$PROJECT_DIR/configs/apt/20auto-upgrades" "$root/etc/apt/apt.conf.d/20auto-upgrades"
install -Dm644 "$PROJECT_DIR/configs/apt/52-vps-linux-unattended-upgrades" "$root/etc/apt/apt.conf.d/52-vps-linux-unattended-upgrades"
# Keep the guest agent enabled but harmless on hosts without the virtio port.
install -Dm644 "$PROJECT_DIR/configs/systemd/qemu-guest-agent.conf" "$root/etc/systemd/system/qemu-guest-agent.service.d/99-vps-linux.conf"
printf 'vps-linux\n' > "$root/etc/hostname"
printf '127.0.0.1 localhost\n127.0.1.1 vps-linux\n::1 localhost ip6-localhost ip6-loopback\n' > "$root/etc/hosts"
printf 'LABEL=VPS_ROOT / ext4 defaults 0 1\nLABEL=VPS_EFI /boot/efi vfat umask=0077 0 2\n' > "$root/etc/fstab"
mkdir -p "$root/boot/efi" "$root/run/sshd" "$root/usr/share/vps-linux"
ln -sfn /run/systemd/resolve/stub-resolv.conf "$root/etc/resolv.conf"
# Do not pre-create a login user. cloud-init creates debian at first boot.
chroot "$root" passwd -l root
! chroot "$root" getent passwd vpsadmin >/dev/null || die 'Unexpected legacy vpsadmin account.'
! chroot "$root" getent passwd debian >/dev/null || die 'debian must be created by cloud-init, not at build time.'
# Debian ships both /usr/bin/docker-compose and its native CLI plugin.
compose_version=$(chroot "$root" /usr/bin/docker-compose version --short)
[[ $compose_version == 2.* || $compose_version == v2.* ]] || die "Expected Compose V2, got: $compose_version"
chroot "$root" docker compose version
# The schema command validates user-data, not /etc/cloud system policy.
install -m644 "$PROJECT_DIR/tests/cloud-init/user-data.example" "$root/tmp/vps-linux-user-data.example"
chroot "$root" cloud-init schema --config-file /tmp/vps-linux-user-data.example
rm -f "$root/tmp/vps-linux-user-data.example"
chroot "$root" /usr/sbin/sshd -t
ssh_config=$(chroot "$root" /usr/sbin/sshd -T)
for policy in 'passwordauthentication no' 'kbdinteractiveauthentication no' 'permitrootlogin no' 'pubkeyauthentication yes' 'maxauthtries 3' 'clientaliveinterval 300' 'requiredrsasize 3072'; do
    grep -Fxq "$policy" <<< "$ssh_config" || die "Missing effective SSH policy: $policy"
done
systemctl --root="$root" enable systemd-networkd.service systemd-resolved.service systemd-timesyncd.service ssh.service docker.service qemu-guest-agent.service apt-daily.timer apt-daily-upgrade.timer fstrim.timer
# cloud-init units are linked by their package; explicitly enable the boot stages.
systemctl --root="$root" enable cloud-init-main.service cloud-init-local.service cloud-init-network.service cloud-config.service cloud-final.service
# dpkg-query owns these format variables.
# shellcheck disable=SC2016
chroot "$root" dpkg-query -W '-f=${binary:Package}\t${Version}\t${Architecture}\n' > "$root/usr/share/vps-linux/packages.tsv"
cp "$root/usr/share/vps-linux/packages.tsv" "$VPS_LINUX_WORK/release/packages.tsv"
printf 'VPS Linux v%s\nDebian-based server image\n' "$VPS_LINUX_VERSION" > "$root/etc/issue"
printf '%s\n' "$VPS_LINUX_VERSION" > "$root/usr/share/vps-linux/version"

printf 'virtio_pci\nvirtio_blk\nvirtio_net\next4\n' >> "$root/etc/initramfs-tools/modules"
: > "$root/usr/share/vps-linux/.build-in-progress"

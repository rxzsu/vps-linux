#!/usr/bin/env bash
# This file is executed INSIDE libguestfs by virt-customize, never on the host.
set -Eeuo pipefail
[[ -f /usr/share/vps-linux/.build-in-progress && -f /usr/share/vps-linux/version && $(cat /usr/share/vps-linux/version) == 0.2-dev ]] || { echo 'Not a VPS Linux build guest' >&2; exit 1; }
cloud-init clean --logs --seed --machine-id
rm -f /etc/ssh/ssh_host_* /var/lib/dbus/machine-id /var/lib/systemd/random-seed
# Empty machine-id triggers first-boot regeneration; retain an existing empty file.
: > /etc/machine-id
ln -s /etc/machine-id /var/lib/dbus/machine-id
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/lib/dhcp/*
find /var/log -type f -exec truncate -s 0 {} +
rm -f /root/.bash_history /root/.ssh/authorized_keys
[[ ! -s /etc/machine-id ]] || exit 1
if compgen -G '/etc/ssh/ssh_host_*' >/dev/null; then echo 'SSH host keys remain' >&2; exit 1; fi
if find /home -mindepth 1 -print -quit | grep -q .; then echo 'Preconfigured home directory remains' >&2; exit 1; fi

rm -f /usr/share/vps-linux/.build-in-progress

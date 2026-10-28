#!/usr/bin/env bash
# Run remotely over the test instance's authenticated SSH connection.
set -Eeuo pipefail
expected_hostname=$1
[[ $(hostname) == "$expected_hostname" ]]
[[ $(uname -m) == x86_64 ]]
# shellcheck disable=SC1091
source /etc/os-release
[[ $ID == debian && $VERSION_ID == 13 ]]
[[ $(sudo -n whoami) == root ]]
[[ $(sudo -n passwd -S root | awk '{print $2}') == L ]]
[[ $(sudo -n passwd -S debian | awk '{print $2}') == L ]]
if getent passwd vpsadmin >/dev/null; then echo "Legacy account remains" >&2; exit 1; fi
[[ $(stat -fc %T /sys/fs/cgroup) == cgroup2fs ]]
ip -4 route show default | grep -q '^default '
systemctl is-active --quiet systemd-networkd.service systemd-resolved.service systemd-timesyncd.service docker.service
cloud-init status --wait --long
[[ -z $(systemctl --failed --no-legend --plain) ]]
config=$(sudo -n /usr/sbin/sshd -T)
for policy in 'passwordauthentication no' 'kbdinteractiveauthentication no' 'permitrootlogin no' 'pubkeyauthentication yes'; do
    grep -Fxq "$policy" <<< "$config"
done
sudo -n docker info --format '{{.Driver}} {{.CgroupVersion}}' | grep -Fxq 'overlay2 2'
sudo -n docker-compose version
sudo -n docker compose version
[[ $(cat /sys/block/zram0/disksize) == 1073741824 ]]
grep -q '\[lz4\]' /sys/block/zram0/comp_algorithm
awk '$1=="/dev/zram0" && $5==100 {found=1} END {exit !found}' /proc/swaps
[[ $(cat /etc/machine-id) =~ ^[a-f0-9]{32}$ ]]
[[ -s /etc/ssh/ssh_host_ed25519_key.pub && -s /etc/ssh/ssh_host_ecdsa_key.pub ]]
[[ ! -e /usr/share/vps-linux/.build-in-progress ]]
printf 'Guest functional/security checks passed\n'

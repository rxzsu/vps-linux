#!/usr/bin/env bash
# Run remotely over the test instance's authenticated SSH connection.
set -Eeuo pipefail
# SSH can be available while Docker and other boot jobs are still starting.
# Wait for systemd to finish booting, without starting/restarting any services.
boot_state=''
if ! boot_state=$(timeout 180 systemctl is-system-running --wait); then
    echo "Guest boot did not reach a healthy running state: $boot_state" >&2
    systemctl --failed --no-legend --plain >&2 || true
    sudo -n journalctl -b -u docker.service -u containerd.service -n 60 --no-pager >&2 || true
    exit 1
fi
[[ $boot_state == running ]] || { echo "Unexpected system state: $boot_state" >&2; exit 1; }
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
for unit in systemd-networkd.service systemd-resolved.service systemd-timesyncd.service docker.service qemu-guest-agent.service apt-daily.timer apt-daily-upgrade.timer; do
    systemctl is-active --quiet "$unit" || { echo "Required unit is not active: $unit" >&2; exit 1; }
done
# Docker: log rotation/live-restore and the disk/log safety limits must be effective.
[[ $(sudo -n docker info --format '{{.LiveRestoreEnabled}}') == true ]]
[[ $(sudo -n docker info --format '{{.LoggingDriver}}') == json-file ]]
grep -Fxq 'SystemMaxUse=200M' /etc/systemd/journald.conf.d/99-vps-linux.conf
# Read the effective merged APT configuration, including Debian's 50-* defaults.
# shellcheck disable=SC2016  # APT expands the literal distro_codename later.
sudo -n /usr/bin/python3 - <<'PY_APT'
import apt_pkg
apt_pkg.init_config()
config = apt_pkg.config
assert config.value_list('Unattended-Upgrade::Allowed-Origins') == []
expected = 'origin=Debian,codename=${distro_codename}-security,label=Debian-Security'
assert config.value_list('Unattended-Upgrade::Origins-Pattern') == [expected]
assert config.find_b('Unattended-Upgrade::Automatic-Reboot') is False
print('Effective unattended-upgrades policy: security only; automatic reboot disabled')
PY_APT
cloud-init status --wait --long
[[ -z $(systemctl --failed --no-legend --plain) ]]
config=$(sudo -n /usr/sbin/sshd -T)
for policy in 'passwordauthentication no' 'kbdinteractiveauthentication no' 'permitrootlogin no' 'pubkeyauthentication yes' 'maxauthtries 3' 'clientaliveinterval 300' 'requiredrsasize 3072'; do
    grep -Fxq "$policy" <<< "$config"
done
# Hardened kernel/network defaults, disabled core dumps and weekly TRIM must be effective.
[[ $(sysctl -n kernel.dmesg_restrict) == 1 ]]
[[ $(sysctl -n kernel.kptr_restrict) == 2 ]]
[[ $(sysctl -n kernel.unprivileged_bpf_disabled) == 1 ]]
[[ $(sysctl -n fs.suid_dumpable) == 0 ]]
[[ $(sysctl -n fs.protected_symlinks) == 1 ]]
[[ $(sysctl -n net.ipv4.conf.all.accept_redirects) == 0 ]]
[[ $(sysctl -n net.ipv4.conf.all.send_redirects) == 0 ]]
grep -Fxq 'Storage=none' /etc/systemd/coredump.conf.d/99-vps-linux.conf
[[ $(systemctl is-enabled fstrim.timer) == enabled ]]
[[ -x /etc/update-motd.d/10-vps-linux ]]
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

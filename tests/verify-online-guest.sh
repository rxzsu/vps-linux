#!/usr/bin/env bash
# Runs only inside a disposable guest, over the harness's authenticated SSH.
set -Eeuo pipefail
[[ $(cat /usr/share/vps-linux/version) =~ ^0\.2(-dev)?$ ]] || { echo 'Not a v0.2 test guest' >&2; exit 1; }
wait_for_time() {
    local deadline=$((SECONDS + 180))
    until [[ $(timedatectl show -p NTPSynchronized --value) == yes ]]; do
        if (( SECONDS >= deadline )); then
            timedatectl status
            sudo -n journalctl -u systemd-timesyncd -n 30 --no-pager
            echo 'NTP synchronization timed out' >&2
            return 1
        fi
        sleep 3
    done
    echo 'NTP synchronization: yes'
}
wait_for_time
if [[ ${1:-} != --after-reboot ]]; then
    sudo -n docker run --rm hello-world
    sudo -n docker run -d --name vps-linux-release-http --restart unless-stopped -p 127.0.0.1:8080:80 nginx:alpine
fi
curl --fail --silent --show-error --retry 30 --retry-connrefused --retry-delay 2 --retry-max-time 90 --max-time 5 http://127.0.0.1:8080/ | grep -q 'Welcome to nginx!'
[[ -z $(systemctl --failed --no-legend --plain) ]]
if [[ ${1:-} == --after-reboot ]]; then
    sudo -n docker rm -f vps-linux-release-http
    echo 'Reboot: Docker HTTP service recovered; NTP synchronized; no failed units'
else
    echo 'Registry pull, hello-world execution and HTTP workload: passed'
fi

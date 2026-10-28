#!/usr/bin/env bash
# Only the read-only cloud-init readiness query may be retried after SSH loss.
wait_for_cloud_init() {
    local vm_pid=$1 budget=$2 deadline remaining status
    shift 2
    deadline=$((SECONDS + budget))
    while :; do
        kill -0 "$vm_pid" 2>/dev/null || { echo 'QEMU exited while waiting for cloud-init.' >&2; return 1; }
        remaining=$((deadline - SECONDS))
        (( remaining > 0 )) || { echo 'Timed out waiting for cloud-init over SSH.' >&2; return 124; }
        status=0
        timeout "$remaining" "$@" 'cloud-init status --wait --long' || status=$?
        case $status in
            0) return 0 ;;
            255) echo 'SSH disconnected during cloud-init readiness; retrying...' >&2 ;;
            *) return "$status" ;;
        esac
        sleep 2
    done
}

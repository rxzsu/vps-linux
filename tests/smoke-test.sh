#!/usr/bin/env bash
# Read-only backing image + two independent overlays; no host root is required.
set -Eeuo pipefail
umask 077
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
if [[ ${1:-} == --help || ${1:-} == -h ]]; then
    printf 'Usage: ./tests/smoke-test.sh IMAGE.qcow2 [--accel auto|kvm|tcg]\nRequires 4 GiB available RAM, QEMU, OVMF, cloud-localds, busybox-static and SSH tools.\n'; exit 0
fi
[[ $# == 1 || ( $# == 3 && $2 == --accel ) ]] || { echo 'Use smoke-test.sh --help' >&2; exit 1; }
accel=${3:-auto}
[[ $accel == auto || $accel == kvm || $accel == tcg ]] || { echo 'Invalid acceleration' >&2; exit 1; }
for tool in qemu-img qemu-system-x86_64 cloud-localds ssh ssh-keygen python3 timeout tar file sha256sum; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
[[ -f $1 && ! -L $1 && $1 == *.qcow2 ]] || { echo 'Image must be a regular QCOW2 file, not a symlink or device.' >&2; exit 1; }
image=$(realpath -e -- "$1")
[[ $image =~ ^/[a-zA-Z0-9._/-]+$ ]] || { echo "Use an image path without spaces, commas or shell metacharacters." >&2; exit 1; }
qemu-img check -f qcow2 "$image"
qemu-img info --output=json --force-share "$image" | python3 "$PROJECT_DIR/scripts/check-image.py"
[[ -f $image.sha256 ]] || { echo 'Missing checksum file.' >&2; exit 1; }
# Check exactly the requested image rather than arbitrary paths in a checksum file.
python3 - "$image" <<'PY'
import hashlib, pathlib, sys
p = pathlib.Path(sys.argv[1])
fields = pathlib.Path(str(p) + '.sha256').read_text().strip().split(maxsplit=1)
if len(fields) != 2 or fields[1].lstrip('*') != p.name:
    sys.exit('Checksum must describe exactly this image basename')
h = hashlib.sha256()
with p.open('rb') as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
if h.hexdigest() != fields[0]:
    sys.exit('Image checksum mismatch')
PY
original_sha=$(sha256sum "$image" | awk '{print $1}')
if [[ $accel == auto ]]; then
    if [[ -r /dev/kvm && -w /dev/kvm ]]; then accel=kvm; else accel=tcg; fi
fi
[[ $accel != kvm || ( -r /dev/kvm && -w /dev/kvm ) ]] || { echo 'KVM was requested but is inaccessible.' >&2; exit 1; }
cpu=max
[[ $accel != kvm ]] || cpu=host
code=''; vars=''
for suffix in _4M ''; do
    if [[ -r /usr/share/OVMF/OVMF_CODE${suffix}.fd && -r /usr/share/OVMF/OVMF_VARS${suffix}.fd ]]; then
        code="/usr/share/OVMF/OVMF_CODE${suffix}.fd"; vars="/usr/share/OVMF/OVMF_VARS${suffix}.fd"; break
    fi
done
[[ -n $code ]] || { echo 'Matching non-Secure-Boot OVMF code/vars pair not found.' >&2; exit 1; }
busybox=$(command -v busybox || true)
if [[ -z $busybox ]] || ! file -L "$busybox" | grep -Eq 'statically linked|static-pie linked'; then
    echo 'Install host busybox-static for the offline Docker test.' >&2; exit 1
fi
busybox=$(realpath -e -- "$busybox")
work=$(mktemp -d /tmp/vps-linux-smoke.XXXXXXXX)
pid=''
stop_vm() {
    if [[ -n $pid ]]; then
        kill "$pid" 2>/dev/null || true
        timeout 10 tail --pid="$pid" -f /dev/null 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
        pid=''
    fi
}
cleanup() {
    local status=$?
    trap - EXIT
    stop_vm
    if (( status != 0 )); then
        # Keep only serial diagnostics in an ignored folder, never the seed/key.
        local diagnostics
        diagnostics="$PROJECT_DIR/output/smoke-failure-$(date -u +%Y%m%dT%H%M%SZ)-$$"
        if [[ ! -L $PROJECT_DIR/output ]] && mkdir -p "$diagnostics" 2>/dev/null; then
            cp "$work"/*.log "$diagnostics/" 2>/dev/null || true
            printf 'Smoke failed. Serial diagnostics: %s\n' "$diagnostics" >&2
        else
            diagnostics=$(mktemp -d /tmp/vps-linux-smoke-failure.XXXXXXXX)
            cp "$work"/*.log "$diagnostics/" 2>/dev/null || true
            printf 'Smoke failed. Serial diagnostics: %s\n' "$diagnostics" >&2
        fi
    fi
    rm -rf -- "$work"
    local after
    after=$(sha256sum "$image" | awk '{print $1}')
    [[ $original_sha == "$after" ]] || { echo 'ERROR: backing image changed!' >&2; status=1; }
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
ssh-keygen -q -t ed25519 -N '' -f "$work/id_ed25519"
# Temporary key is never printed and is removed by the exit trap.
python3 - "$work" "$busybox" <<'PY'
import pathlib, sys, tarfile
work = pathlib.Path(sys.argv[1])
with tarfile.open(work / 'container.tar', 'w') as archive:
    archive.add(sys.argv[2], arcname='busybox', recursive=False)
PY
for instance in a b; do
    hostname="vps-linux-smoke-$instance"
    qemu-img create -f qcow2 -F qcow2 -b "$image" "$work/$instance.qcow2"
    cp "$vars" "$work/$instance-vars.fd"
    {
        printf '#cloud-config\nhostname: %s\nusers: [default]\nssh_authorized_keys:\n  - ' "$hostname"
        cat "$work/id_ed25519.pub"
    } > "$work/user-data"
    printf 'instance-id: vps-linux-smoke-%s\nlocal-hostname: %s\n' "$instance" "$hostname" > "$work/meta-data"
    cloud-localds "$work/seed.iso" "$work/user-data" "$work/meta-data"
    port=$(python3 - <<'PY'
import socket
with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    print(s.getsockname()[1])
PY
)
    qemu-system-x86_64 -nodefaults -machine "q35,accel=$accel" -cpu "$cpu" -m 2048 -smp 2 \
        -display none -monitor none -serial "file:$work/$instance-serial.log" \
        -drive "if=pflash,format=raw,readonly=on,file=$code" \
        -drive "if=pflash,format=raw,file=$work/$instance-vars.fd" \
        -drive "if=virtio,format=qcow2,file=$work/$instance.qcow2" \
        -drive "if=virtio,format=raw,readonly=on,file=$work/seed.iso" \
        -device virtio-net-pci,netdev=net0 -device virtio-rng-pci \
        -netdev "user,id=net0,hostfwd=tcp:127.0.0.1:$port-:22" > "$work/$instance-qemu.log" 2>&1 &
    pid=$!
    ssh_opts=(-p "$port" -i "$work/id_ed25519" -o BatchMode=yes -o IdentitiesOnly=yes -o PasswordAuthentication=no -o StrictHostKeyChecking=accept-new -o "UserKnownHostsFile=$work/$instance-known-hosts" -o GlobalKnownHostsFile=/dev/null -o ConnectTimeout=3 -o LogLevel=ERROR)
    deadline=$((SECONDS + 900))
    until ssh "${ssh_opts[@]}" debian@127.0.0.1 true 2>/dev/null; do
        kill -0 "$pid" 2>/dev/null || { echo 'QEMU exited before SSH became ready.' >&2; exit 1; }
        (( SECONDS < deadline )) || { echo 'Timed out waiting for SSH.' >&2; exit 1; }
        sleep 2
    done
    timeout 600 ssh "${ssh_opts[@]}" debian@127.0.0.1 'cloud-init status --wait --long'
    timeout 180 ssh "${ssh_opts[@]}" debian@127.0.0.1 "bash -s -- $hostname" < "$PROJECT_DIR/tests/verify-guest.sh"
    timeout 60 ssh "${ssh_opts[@]}" debian@127.0.0.1 'sudo -n docker import - vps-linux-smoke' < "$work/container.tar"
    [[ $(timeout 60 ssh "${ssh_opts[@]}" debian@127.0.0.1 'sudo -n docker run --rm --network=none vps-linux-smoke /busybox echo vps-linux-container-ok') == vps-linux-container-ok ]]
    ssh "${ssh_opts[@]}" debian@127.0.0.1 'cat /etc/machine-id' > "$work/$instance-machine-id"
    ssh "${ssh_opts[@]}" debian@127.0.0.1 'ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub' > "$work/$instance-host-key"
    if ssh "${ssh_opts[@]}" root@127.0.0.1 true 2>/dev/null; then echo 'Root SSH login unexpectedly succeeded' >&2; exit 1; fi
    stop_vm
    rm -f "$work/seed.iso"
    printf 'Instance %s: UEFI, cloud-init, SSH, Docker, network, ZRAM and NTP service checks passed\n' "$instance"
done
! cmp -s "$work/a-machine-id" "$work/b-machine-id" || { echo 'machine-id was reused' >&2; exit 1; }
! cmp -s "$work/a-host-key" "$work/b-host-key" || { echo 'SSH host key was reused' >&2; exit 1; }
printf 'PASS: two fresh instances have distinct machine IDs and SSH host keys.\n'
printf 'NTP synchronization and external registry access: NOT RUN (offline smoke).\n'

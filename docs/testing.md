# Testing and first boot

## Static checks

```sh
./tests/static-checks.sh
```

Bash syntax, ShellCheck, 16 Python tests: image admission, cleanup path/symlink protection, CLI rejection, YAML policy, ZRAM, Docker, public key fingerprints and workflow syntax. Dependencies: ShellCheck, Python 3, PyYAML, GnuPG. These tests do not prove an image boots.

## Automated acceptance test

After a successful build, use the exact image path printed by `build.sh`:

```sh
./tests/smoke-test.sh output/<build-id>/vps-linux-v0.2-dev.qcow2
# If KVM is unavailable:
./tests/smoke-test.sh output/<build-id>/vps-linux-v0.2-dev.qcow2 --accel tcg
```

The runner checks integrity and the supplied checksum, rejects external backing/data files, and launches **two independent QCOW2 overlays** of the read-only candidate. Each guest gets a fresh OVMF vars file, unique NoCloud instance ID/hostname and a temporary SSH public key. The private key stays in a mode-0700 `/tmp` directory and is removed on every normal/error/signal exit. Test keys/seed data are never put in the candidate. SIGKILL cannot run cleanup traps; inspect and remove only the abandoned test directory and its specific QEMU process after an interrupted run.

QEMU uses user-mode NAT with SSH forwarded only on `127.0.0.1` and an automatically selected port. Port allocation has a small race; if another process takes the port, the runner detects QEMU exit and fails. No host bridge, TAP or privileged networking is needed. A private known-hosts file uses `accept-new`; host key checking is not globally disabled. One VM runs at a time with 2 vCPU/2 GiB RAM. Allow 900 seconds per boot and 600 seconds for cloud-init; each functional/container phase has a timeout. TCG can be slow on overloaded hosts.

Assertions:

- QCOW2 structure, declared 8 GiB size, SHA256 and unchanged backing artifact;
- UEFI boot, Debian 13/x86_64, DHCP default route;
- cloud-init completion without degraded/error exit, hostname and provisioned `debian` key login;
- passwordless sudo, locked user/root passwords, no legacy account;
- effective SSH password/keyboard-interactive/root denial and a rejected root login;
- Docker daemon, overlay2, cgroups v2 and both Compose V2 interfaces;
- **real offline container execution** by importing the host's trusted static BusyBox binary into the disposable guest; no external image registry needed;
- 1 GiB ZRAM, LZ4, swap priority 100;
- resolved/networkd/timesyncd active and no failed systemd units;
- fresh valid machine-id and ed25519/ECDSA host keys, distinct IDs/ed25519 fingerprints between two instances.

The default test checks NTP **service activity**, not actual time synchronization. External registry pulls and NTP synchronization are **not run** by the offline suite. For release validation on an Internet-connected Zorin host, additionally check `timedatectl show -p NTPSynchronized --value` equals `yes`, `sudo docker run --rm hello-world`, and an HTTP container workload. Keep these outcomes separate.

On failure serial/QEMU logs are copied into ignored `output/smoke-failure-*`, or `/tmp/vps-linux-smoke-failure.*` if output is not writable. Seeds, overlays and private keys are removed. Review logs before sharing; they can contain public keys and instance details. Success is determined by exit status 0, not a partially printed progress message.

## Manual NoCloud seed

Start from a disposable overlay and your own public key. Run from the checkout:

```sh
mkdir -p output/manual-test
qemu-img create -f qcow2 -F qcow2 \
  -b "$(realpath output/<build-id>/vps-linux-v0.2-dev.qcow2)" \
  output/manual-test/disk.qcow2
cp tests/cloud-init/user-data.example output/manual-test/user-data
cp tests/cloud-init/meta-data.example output/manual-test/meta-data
```

Edit `output/manual-test/user-data` and replace the placeholder with the full contents of your **public** `~/.ssh/id_ed25519.pub` key. Set a fresh instance-id in meta-data for a new instance. Never copy the private key into NoCloud data.

```sh
cloud-localds output/manual-test/seed.iso \
  output/manual-test/user-data output/manual-test/meta-data
cp /usr/share/OVMF/OVMF_VARS_4M.fd output/manual-test/vars.fd
qemu-system-x86_64 -machine q35,accel=kvm -cpu host -m 2048 -smp 2 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
  -drive if=pflash,format=raw,file=output/manual-test/vars.fd \
  -drive if=virtio,format=qcow2,file=output/manual-test/disk.qcow2 \
  -drive if=virtio,format=raw,readonly=on,file=output/manual-test/seed.iso \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22 \
  -device virtio-net-pci,netdev=net0 -display none -serial mon:stdio
```

If your firmware package uses the unsuffixed CODE/VARS filenames, use that matching pair. Keep Secure Boot off. Without KVM substitute `accel=tcg -cpu max`. In another terminal:

```sh
ssh -p 2222 -i ~/.ssh/id_ed25519 debian@127.0.0.1
# In the guest:
cloud-init status --wait --long
sudo whoami
docker-compose version
docker compose version
```

The manual path uses your own normal SSH host-key verification. An old known-host entry after recreating a guest is expected to cause a warning; verify that it belongs to this disposable instance before replacing it. Stop QEMU with the monitor or Ctrl-A X in the serial monitor; never delete an overlay while its QEMU process is still running.

## CI

`.github/workflows/validate-build-system.yml` runs static checks on the development branch and relevant PRs. A manual workflow_dispatch with `build_and_boot=true` installs tools on an Ubuntu 24.04 runner, builds and boots with TCG. This workflow has not yet run; GitHub runner success does not replace required local Zorin validation. It uploads metadata only, never images/keys, and does not publish releases or deploy the website.

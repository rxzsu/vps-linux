# Testing and first boot

## Static checks

```sh
./tests/static-checks.sh
```

Bash syntax, ShellCheck, 36 Python tests: image admission, cleanup path/symlink protection, CLI rejection, YAML policy, ZRAM, Docker logging/live-restore, journald limits, unattended-upgrade policy, public key fingerprints and workflow syntax. Dependencies: ShellCheck, Python 3, PyYAML, GnuPG, qemu-utils, minisign and apt-config. Integrity tests use real sparse QCOW2 files and ephemeral minisign keys; they do not boot VMs. These tests do not prove an image boots.

## Automated acceptance test

After a successful build, use the exact image path printed by `build.sh`:

```sh
./tests/smoke-test.sh output/<build-id>/vps-linux-v0.3-dev.qcow2
# If KVM is unavailable:
./tests/smoke-test.sh output/<build-id>/vps-linux-v0.3-dev.qcow2 --accel tcg
```

The runner checks integrity and the supplied checksum, rejects external backing/data files, and launches **two independent QCOW2 overlays** of the read-only candidate. Each guest gets a fresh OVMF vars file, unique NoCloud instance ID/hostname and a temporary SSH public key. The private key stays in a mode-0700 `/tmp` directory and is removed on every normal/error/signal exit. Test keys/seed data are never put in the candidate. SIGKILL cannot run cleanup traps; inspect and remove only the abandoned test directory and its specific QEMU process after an interrupted run.

QEMU uses user-mode NAT with SSH forwarded only on `127.0.0.1` and an automatically selected port. Port allocation has a small race; if another process takes the port, the runner detects QEMU exit and fails. No host bridge, TAP or privileged networking is needed. A private known-hosts file uses `accept-new`; host key checking is not globally disabled. One VM runs at a time with 2 vCPU/2 GiB RAM. Allow 900 seconds per boot and 600 seconds for cloud-init; each functional/container phase has a timeout. TCG can be slow on overloaded hosts.

Assertions:

- QCOW2 structure, declared 8 GiB size, SHA256 and unchanged backing artifact;
- UEFI boot, Debian 13/x86_64, DHCP default route;
- cloud-init completion without degraded/error exit, hostname and provisioned `debian` key login;
- passwordless sudo, locked user/root passwords, no legacy account;
- effective SSH password/keyboard-interactive/root denial and a rejected root login;
- Docker daemon, overlay2, cgroups v2, both Compose V2 interfaces, `json-file` logging with `10m`/3-file rotation and `live-restore`;
- journald limits (`SystemMaxUse=200M`), enabled `apt-daily` timers and security-only unattended upgrades without automatic reboot;
- active `qemu-guest-agent` and a successful read-only `guest-ping` through an explicitly attached virtio-serial port;
- **real offline container execution** by importing the host's trusted static BusyBox binary into the disposable guest; no external image registry needed;
- 1 GiB ZRAM, LZ4, swap priority 100;
- resolved/networkd/timesyncd active and no failed systemd units;
- instance B starts from a 10 GiB overlay and must grow its GPT root partition and ext4 filesystem beyond 9 GiB; primary/backup GPT locations and header CRCs are checked;
- fresh valid machine-id and ed25519/ECDSA host keys, distinct IDs/ed25519 and ECDSA fingerprints between two instances.

The default test checks NTP **service activity**, not actual time synchronization. External registry pulls and NTP synchronization are **not run** by the offline suite. For release validation on an Internet-connected Zorin host, additionally check `timedatectl show -p NTPSynchronized --value` equals `yes`, `sudo docker run --rm hello-world`, and an HTTP container workload. Keep these outcomes separate.

On failure serial/QEMU logs are copied into ignored `output/smoke-failure-*`, or `/tmp/vps-linux-smoke-failure.*` if output is not writable. Seeds, overlays and private keys are removed. Review logs before sharing; they can contain public keys and instance details. Success is determined by exit status 0, not a partially printed progress message.

## Manual NoCloud seed

Start from a disposable overlay and your own public key. Run from the checkout:

```sh
mkdir -p output/manual-test
qemu-img create -f qcow2 -F qcow2 \
  -b "$(realpath output/<build-id>/vps-linux-v0.3-dev.qcow2)" \
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

`.github/workflows/validate-build-system.yml` runs static checks on pushes to `main` and relevant pull requests. A manual workflow_dispatch with `build_and_boot=true` frees runner disk space, installs host tools on Ubuntu 24.04, builds the candidate, runs the two-instance smoke suite under TCG (including the 10 GiB disk-growth check), verifies `SHA256SUMS`/SBOM, then keyless-signs `SHA256SUMS` with cosign through the workflow OIDC identity. It uploads only metadata, SBOM, checksums, the signature bundle and failure serial logs — never the image or private keys — and does not publish releases or deploy the website. Verify a downloaded signature with `scripts/verify-release.sh`. GitHub runner success does not replace required local Zorin validation.

## Extended pre-release check

```sh
./tests/smoke-test.sh output/<build-id>/vps-linux-v0.3-dev.qcow2 --release-check
```

This opt-in mode needs guest Internet access to NTP servers and Docker Hub. It runs the offline checks on both disposable instances, and additionally on instance A waits for actual NTP synchronization, pulls/runs hello-world and nginx, verifies HTTP, reboots the guest, waits for a changed boot ID, reruns functional/security checks and checks that machine-id and both SSH host keys persist. It then checks the HTTP container restarts, NTP resynchronizes and no systemd units fail. All phases have bounded timeouts; network failures fail the check rather than being marked passed. The backing image remains unchanged.

The extended VM mode has not been executed in the managed authoring environment. The owner reported a successful local build on Zorin and a passing extended run covering actual NTP synchronization, Docker Hub pulls, an HTTP workload, reboot with persistent identities and no failed units. The offline two-instance smoke checks also passed. These results are owner-reported; the managed cloud environment did not boot the image. See [validation status](validation.md).

## One-command v0.3 local build and acceptance

On the Zorin/Noble host prepared for v0.2, install the additional integrity-test tools and run:

```sh
sudo apt-get install -y minisign shellcheck python3-yaml
./tests/v0.3-check.sh
```

For a new host, install all prerequisites in [building.md](building.md) first. The wrapper requires sudo, validates the host, runs all static/integrity tests, creates an **ephemeral unencrypted test-only minisign key outside the checkout**, builds 0.3-dev with a signature, verifies the complete bundle and signature, and runs the extended two-instance VM harness (including guest-ping, effective APT policy, effective container log rotation, disk growth/GPT checks, online tests and reboot). No manual VM setup is required. It prints the exact acceptance JSON path on success. Existing v0.1/v0.2 artifacts are not modified.

The private test key is deleted by the exit trap; only its public key and the acceptance report are retained in ignored output/. A test key is **not** a production release trust root and these artifacts are not published. SIGKILL cannot execute traps; remove only the specific abandoned temporary directory after confirming no build uses it. Keyless cosign verification still requires the GitHub Actions OIDC workflow; a local minisign pass is not a keyless pass.

The bundle verifier requires every mandatory artifact to be covered by SHA256SUMS, hashes the actual bytes, checks metadata and the exact SBOM package identities/versions/architectures, verifies an optional signature, then checks the QCOW2 structure. It rejects omitted files, traversal/duplicate checksum entries, symlinks, unrelated same-count SBOMs, mismatched metadata, fake QCOW2 payloads, modified signatures and wrong trust keys. The SPDX namespace hashes the document content rather than only the source revision. New package manifests include binary name, version and architecture; old two-column input remains readable without inventing an unknown architecture.

# VPS Linux

**Your server. Nothing unnecessary.**

VPS Linux is an independent, purpose-configured Debian-based server image for VPS hosting, QEMU/KVM and Docker workloads. It uses Debian packages and security maintenance; it is not a replacement distribution built from scratch.

- **Stable:** [v0.1](https://github.com/rxzsu/vps-linux/releases/tag/v0.1), manually assembled and tested.
- **Development:** v0.2 build automation, on `feature/v0.2-build-system`. A development candidate passed owner-reported Zorin build/boot/online/reboot checks; the final 0.2 candidate still needs building and testing. No v0.2 release is published.
- **Website:** https://vps-linux1.companiumpidors.workers.dev/ (English and Russian).
- **License:** [MIT](LICENSE).

## Stable v0.1

Debian 13 Trixie, x86_64, Linux 6.12 (tested kernel `6.12.107+deb13-amd64`), UEFI/GRUB, QCOW2 with an 8 GiB virtual disk. Tested under QEMU/KVM with 2 vCPUs and 2 GiB RAM.

- Debian Docker Engine (`docker.io`) 26.1.5 and Compose V2 2.26.1 in the original test. The verified v0.1 interface is **`docker-compose`**; do not assume `docker compose` is available there.
- systemd-networkd DHCP, resolved DNS and timesyncd time synchronization.
- 1 GiB ZRAM, LZ4, swap priority 100.
- SSH public-key authentication; password, keyboard-interactive and direct root SSH login disabled.
- cloud-init NoCloud provisioning tested, including hostname, `debian` user/public key, passwordless sudo and regenerated machine-id/SSH host keys. A locked legacy `vpsadmin` account existed in v0.1; v0.2 does not pre-create it.

Download the [v0.1 QCOW2 and SHA256](https://github.com/rxzsu/vps-linux/releases/tag/v0.1). Existing release assets remain unchanged. The published v0.1 image was tested on disposable copies; its manual assembly cannot be reconstructed exactly from this repository.

## v0.2 development build

The first iteration implements mmdebstrap → configured Debian rootfs → libguestfs GPT/EFI/ext4 disk → removable UEFI GRUB → standalone QCOW2 + SHA256/package manifest/build metadata.

```sh
# Install prerequisites from docs/building.md first.
./tests/static-checks.sh
sudo ./build.sh --check
sudo ./build.sh
# Use the exact output path printed by the builder:
./tests/smoke-test.sh output/<build-id>/vps-linux-v0.2.qcow2
```

**Development-candidate acceptance passed on the owner’s Zorin host. The final-version artifact must be rebuilt from clean source and tested using `./tests/release-check.sh`.** See [validation evidence and blockers](docs/validation.md). A build exit status alone is not boot verification. This targets a repeatable procedure; byte-for-byte reproducibility is not claimed.

- [Host setup and building](docs/building.md)
- [Architecture and security policy](docs/architecture.md)
- [QEMU/NoCloud testing and SSH provisioning](docs/testing.md)
- [Release gates](docs/releasing.md)

Generated root filesystems, images, seeds and keys are ignored and must never be committed. Scripts accept file-backed images only and never target host physical disks.

## Website

The existing Vue 3/TypeScript/Vite/Tailwind/Motion frontend is in [`website/`](website/). Cloudflare deployment and its static root path are preserved. The **RU / EN** switch saves the user's choice; direct language links use `?lang=ru` / `?lang=en`.

```sh
cd website
bun install --frozen-lockfile
bun run dev
bun run build
# With Playwright Chromium installed, or CHROMIUM_PATH=/usr/bin/chromium:
bun run test
```

See [website/README.md](website/README.md). The OS validation workflow does not deploy the website or publish images.

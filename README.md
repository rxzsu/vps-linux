# VPS Linux

**Your server. Nothing unnecessary.**

VPS Linux is an independent, purpose-configured Debian-based server image for VPS hosting, QEMU/KVM and Docker workloads. It uses Debian packages and security maintenance; it is not a replacement distribution built from scratch.

- **Stable:** [v0.2](https://github.com/rxzsu/vps-linux/releases/tag/v0.2), built by the automated build system and boot-tested. [v0.1](https://github.com/rxzsu/vps-linux/releases/tag/v0.1) remains available as the legacy manually assembled release; its assets are unchanged.
- **Development:** `main`, targeting v0.3. `VERSION` is `0.3-dev`; no v0.3 release exists.
- **Website:** https://vps-linux.vercel.app/ (English and Russian).
- **License:** [MIT](LICENSE).

## Stable v0.2

v0.2 was published on 2026-10-28 from clean source commit `7d0ec202786edc037816a946146f1b40912515eb`. The image implements mmdebstrap → configured Debian rootfs → libguestfs GPT/EFI/ext4 disk → removable UEFI GRUB → standalone QCOW2 + SHA256/package manifest/build metadata.

- Published image SHA256: `c5db7d6edde16f566ec646735d9b41e4bdb22996014407a8fd338d79435d176c`, matching `vps-linux-v0.2.qcow2.sha256` and `build.json`.
- Owner-reported Zorin acceptance passed two independent UEFI boots, NoCloud/SSH policy, Docker and both Compose interfaces, DHCP, ZRAM, NTP synchronization, Docker Hub pulls, HTTP workload and reboot with persistent identities. See [validation evidence](docs/validation.md).
- `build.json` records `source_dirty: false`; its immutable `boot_smoke_test: not_run` field predates the separate acceptance run.

Download the [v0.2 QCOW2 and SHA256](https://github.com/rxzsu/vps-linux/releases/tag/v0.2). A build exit status alone is not boot verification. The procedure is repeatable; byte-for-byte reproducibility is not claimed.

## Stable v0.1

Debian 13 Trixie, x86_64, Linux 6.12 (tested kernel `6.12.107+deb13-amd64`), UEFI/GRUB, QCOW2 with an 8 GiB virtual disk. Tested under QEMU/KVM with 2 vCPUs and 2 GiB RAM.

- Debian Docker Engine (`docker.io`) 26.1.5 and Compose V2 2.26.1 in the original test. The verified v0.1 interface is **`docker-compose`**; do not assume `docker compose` is available there.
- systemd-networkd DHCP, resolved DNS and timesyncd time synchronization.
- 1 GiB ZRAM, LZ4, swap priority 100.
- SSH public-key authentication; password, keyboard-interactive and direct root SSH login disabled.
- cloud-init NoCloud provisioning tested, including hostname, `debian` user/public key, passwordless sudo and regenerated machine-id/SSH host keys. A locked legacy `vpsadmin` account existed in v0.1; v0.2 does not pre-create it.

Download the [v0.1 QCOW2 and SHA256](https://github.com/rxzsu/vps-linux/releases/tag/v0.1). Existing release assets remain unchanged. The published v0.1 image was tested on disposable copies; its manual assembly cannot be reconstructed exactly from this repository.

## v0.3 development

`VERSION` is `0.3-dev`. Work after the v0.2 tag targets the next version; never rebuild a changed tree under the published `0.2` label.

```sh
# Install prerequisites from docs/building.md first.
./tests/static-checks.sh
sudo ./build.sh --check
sudo ./build.sh
# Use the exact output path printed by the builder:
./tests/smoke-test.sh output/<build-id>/vps-linux-v0.3-dev.qcow2
```

A development build is not a release. Stable candidates require a clean checkout, and their bundle must pass `./tests/release-check.sh` before any tag or publication. Verify any bundle with `./scripts/verify-release.sh <bundle>`; it checks `SHA256SUMS` and the SPDX SBOM, and optionally a minisign or keyless cosign signature.

v0.3 development adds capped Docker container logs with `live-restore`, journald storage limits, security-only `unattended-upgrades` with no automatic reboot, an enabled-but-guarded `qemu-guest-agent`, and a 10 GiB overlay disk-growth check. Build bundles now include `sbom.spdx.json` and `SHA256SUMS`; CI keyless-signs the checksums.

- [Host setup and building](docs/building.md)
- [Architecture and security policy](docs/architecture.md)
- [QEMU/NoCloud testing and SSH provisioning](docs/testing.md)
- [Release gates](docs/releasing.md)

Generated root filesystems, images, seeds and keys are ignored and must never be committed. Scripts accept file-backed images only and never target host physical disks.

## Website

The Vue 3/TypeScript/Vite/Tailwind/Motion frontend is in [`website/`](website/) and deploys to Vercel as a static site. Vercel uses `website/` as the project root, builds `dist/` with Bun and applies the security/cache headers from [`website/vercel.json`](website/vercel.json). The **RU / EN** switch saves the user's choice; direct language links use `?lang=ru` / `?lang=en`.

```sh
cd website
bun install --frozen-lockfile
bun run dev
bun run build
# With Playwright Chromium installed, or CHROMIUM_PATH=/usr/bin/chromium:
bun run test
```

See [website/README.md](website/README.md) for Vercel import settings, the custom-domain checklist and validation notes. The OS validation workflow does not deploy the website or publish images.

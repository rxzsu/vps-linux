# VPS Linux

VPS Linux is a lightweight Debian-based Linux image designed for VPS hosting and Docker workloads.

## Version

Current release: **v0.1**

## Features

- Debian 13 (Trixie), x86_64
- Linux 6.12 kernel
- UEFI boot with GRUB
- Docker Engine and Docker Compose
- SSH key authentication
- Password SSH login disabled
- cloud-init support
- DHCP networking via systemd-networkd
- systemd-resolved
- 1 GiB ZRAM with LZ4 compression
- systemd-timesyncd for NTP
- QCOW2 disk image for QEMU/KVM

## System requirements

- QEMU/KVM-compatible virtualization
- 2 GiB RAM recommended
- 2 virtual CPUs recommended
- 8 GiB virtual disk

## Security

The image uses SSH key authentication and disables SSH password login and direct root SSH access.

Use cloud-init to configure your instance and provide your public SSH key.

## Build

The v0.1 image was assembled and tested manually.

Reproducible build scripts are not yet available. They will be added in future updates.

## Download

The QCOW2 image will be published under GitHub Releases.

## Status

**VPS Linux v0.1 — initial release**

## Website

The official website is prepared for Cloudflare Pages at https://vps-linux.pages.dev/. The address is a deployment default; this repository does not provision that hostname.

The frontend lives in [`website/`](website/). It uses Vue 3, strict TypeScript, Vite, Tailwind CSS v4, Motion for Vue and Lucide.

```sh
cd website
bun install --frozen-lockfile
bun run dev
# Type-check and produce the static site
bun run build
# Browser smoke tests (requires Chromium or Playwright's Chromium)
bun run test
```

See [website/README.md](website/README.md) for deployment and validation.

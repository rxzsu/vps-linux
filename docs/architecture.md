# Image architecture

VPS Linux is a purpose-configured Debian server image, not a new distribution replacing Debian. Debian packages supply the kernel, bootloader, userspace and security maintenance. This repository supplies the package selection, configuration, build orchestration and acceptance tests.

## Build stages

1. `build.sh` / `scripts/common.sh`: validate host, safe paths and space; acquire a lock and create a marked private workspace.
2. `scripts/bootstrap.sh`: verified Debian bootstrap using mmdebstrap minbase in a private mount/PID namespace. Package installs cannot start host services; mmdebstrap manages chroot service inhibition.
3. `scripts/configure.sh`: apply the tracked policy files; inspect effective SSH settings and both Compose interfaces; record packages. It is an internal hook and rejects roots outside the active work directory.
4. `scripts/create-image.sh`: create a sparse raw disk and populate GPT/EFI/ext4 in a libguestfs appliance. `/dev/sda` in this script denotes only the appliance's sole newly created file-backed disk, **never the host's `/dev/sda`**. No host loop, NBD or physical block device is accepted.
5. `scripts/install-bootloader.sh`: libguestfs mounts guest filesystems using fstab, regenerates initramfs, installs UEFI fallback GRUB, generates grub.cfg and runs guest-only cleanup without network access.
6. `scripts/cleanup-guest.sh`: require a transient build marker; clean cloud-init, machine-id, host keys, logs, caches and random seed. A built image contains no pre-created user homes or SSH authorized keys.
7. `scripts/package.sh`: convert to standalone QCOW2, validate structure and checksum, write the package manifest/build metadata, generate a deterministic SPDX 2.3 SBOM from the manifest, and checksum every bundle artifact in `SHA256SUMS`. An optional local minisign key can sign that file; CI signs it keylessly with cosign. `build.sh` atomically moves the complete output bundle into place.

## First boot policy

- Supported initial datasource: **NoCloud**, including local seed images. Other providers/datasources are not validated.
- cloud-init creates the `debian` user. The build creates neither `debian` nor legacy `vpsadmin`.
- `debian` has a locked password, sudo without a password and Docker group membership. Both sudo and access to the Docker socket confer root-equivalent control. Provide only trusted SSH public keys.
- Root's password is locked. SSH password, keyboard-interactive and root login are disabled. `00-vps-linux.conf` deliberately precedes other SSH drop-ins because OpenSSH uses the first configured value.
- SSH host keys (ed25519 and ECDSA) and machine-id are generated fresh. Test credentials never enter the source or candidate artifact.
- systemd-networkd owns DHCP for `en*` / `eth*` interfaces, resolved owns DNS and timesyncd owns time synchronization. cloud-init network rendering is disabled to avoid competing configurations. Additional/custom interface names require a separate reviewed configuration.
- Docker uses overlay2 and cgroups v2. Debian's `docker-compose` package already supplies `/usr/bin/docker-compose` and `/usr/libexec/docker/cli-plugins/docker-compose`; the build verifies `docker compose` as well. Container logs use `json-file` with `max-size=10m`/`max-file=3` and `live-restore` keeps containers running across a daemon restart.
- journald is capped at 200 MiB persistent / 50 MiB runtime storage. `unattended-upgrades` applies Debian security updates only and never reboots automatically.
- `qemu-guest-agent` is enabled but starts only when `/dev/virtio-ports/org.qemu.guest_agent.0` exists, so hosts without the device do not report a failed unit.
- systemd-zram-generator creates a 1024 MiB LZ4 swap device at priority 100.

## Compatibility boundaries

Initial target: x86_64, UEFI without Secure Boot, virtio storage/network, 2 vCPUs and 2 GiB guest RAM. The image ships an 8 GiB virtual disk; cloud-init grows the GPT root partition and ext4 filesystem when the attached disk is larger, and the smoke suite verifies this with a 10 GiB overlay. There is no BIOS/ARM build, cloud-provider integration guarantee or signed boot chain. v0.2 is published; byte-for-byte reproducibility is not claimed.

# Building v0.2-dev

This is the first build-system iteration, **not a released or boot-verified v0.2**. v0.1 remains the manually assembled stable release. See [validation status](validation.md) before relying on this implementation.

## Supported host target

Native x86_64 Ubuntu 24.04 / Zorin based on Noble, or Debian 13. The cloud authoring environment is Debian 13 without root or QEMU; the full build has not yet been validated on either target. Use a full host/VM, not a restricted container. Root and private mount/PID namespaces are required for the bootstrap; disk partitioning happens inside libguestfs and never touches a host disk.

Use a checkout path containing only letters, digits, dots, underscores, slashes and hyphens, for example `~/vps-linux`. Paths with spaces/commas are rejected rather than interpolated into appliance/QEMU commands. Reserve at least 20 GiB free disk space and 4 GiB available RAM. These are conservative prerequisites, not measured resource usage. Build time and artifact size have not yet been measured.

## Host dependencies (Ubuntu 24.04/Zorin Noble)

```sh
sudo apt-get update
sudo apt-get install -y \
  mmdebstrap libguestfs-tools qemu-utils qemu-system-x86 ovmf \
  cloud-image-utils busybox-static gnupg dosfstools e2fsprogs \
  python3 python3-yaml shellcheck git util-linux
```

Debian 13 uses the same package names. A readable installed host kernel is required by libguestfs/supermin. Run `sudo libguestfs-test-tool` if its appliance cannot start. KVM is optional; libguestfs and the test runner can use software emulation, which is slower. Secure Boot must be off for this initial unsigned GRUB build.

## Build

```sh
git switch feature/v0.2-build-system
./tests/static-checks.sh
sudo ./build.sh --check
mkdir -p output
sudo ./build.sh
```

`--check` validates host tools, privileges, architecture, OS, disk space, path safety and namespace support without creating an image. There are no options to specify block devices or overwrite existing artifacts. `build.sh` creates a unique private work directory under `output/`, uses a build lock and publishes a complete bundle by directory rename. Stages run in separate process groups; interruption terminates the active stage before cleanup. Its exit trap removes only its marked work directory, refusing to recursively remove a mounted, symlinked or unmarked path.

If the process is terminated with SIGKILL or the machine loses power, no shell trap can run. Private namespace mounts disappear with their processes; an incomplete hidden work directory may remain. Verify no build process is still running before manually removing that specific directory. Never run recursive deletion on a mounted rootfs or a physical disk.

## Outputs

A successful build prints a path such as:

```text
output/vps-linux-v0.2-dev-<UTC timestamp>-<commit>/
  vps-linux-v0.2-dev.qcow2
  vps-linux-v0.2-dev.qcow2.sha256
  packages.tsv
  build.json
```

The disk is an 8 GiB QCOW2 with GPT, a 512 MiB FAT EFI System Partition and ext4 root. Labels `VPS_EFI` and `VPS_ROOT` are used in fstab. Do not attach multiple clones with these same labels to one running guest. GRUB installs `EFI/BOOT/BOOTX64.EFI` via `--removable --no-nvram`; no host UEFI entry is written. The kernel has virtio drivers in its initramfs, and logs to ttyS0.

The bundle is read-only by file mode as a guard against accidents, not cryptographically immutable. Always test overlays, not the backing artifact. The build performs `qemu-img check`, format/size/backing-file validation and SHA256 generation/verification. It does **not** claim boot success; run [the smoke test](testing.md).

## Package inputs and repeatability

Only official Debian `trixie`, `trixie-updates` and `trixie-security` main repositories are used. Vendored [public archive keys](../configs/apt/README.md) provide the initial trust roots; APT signature and artifact-checksum verification stays enabled. No third-party Docker repository is used, and no proxy settings/credentials are stored in the guest.

The goal is a repeatable procedure, still awaiting its first full local build/boot validation. Packages are not version-locked or snapshot-pinned. Apt archives move; filesystem UUIDs, build timestamps and metadata vary. **Byte-for-byte reproducibility has not been implemented or verified.** `packages.tsv` records exact installed versions; `build.json` records the source commit, dirty status and digests. These are audit records, not enough to reconstruct packages that disappear from mirrors.

## Troubleshooting

- Missing command/root/namespace error: install the prerequisites or use a full supported host. Do not weaken the checks or try a physical disk.
- APT signature error: check the clock, repository availability and Debian key-rotation notices. Do not use `trusted=yes`, `--no-check-gpg` or disable TLS.
- libguestfs appliance error: run `sudo libguestfs-test-tool`, check available RAM, host kernel and KVM permissions. Use `LIBGUESTFS_BACKEND=direct`; this builder sets it itself.
- Compose version/interface failure: the build fails before packaging. Keep the Debian V2 package and inspect the actual package version; do not silently substitute Compose V1.
- Failed bootstrap/image stages: the unpublished work directory is removed; keep terminal output for diagnosis. Do not paste credentials or the full process environment.

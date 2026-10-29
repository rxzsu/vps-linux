# Building VPS Linux

This document describes the v0.5 candidate, including vpsctl 0.5.0. Existing published images remain unchanged. Byte-for-byte reproducibility is not claimed. See [validation status](validation.md) for what was actually executed.

## Supported host target

Native x86_64 Ubuntu 24.04 / Zorin based on Noble, or Debian 13. The full v0.2 build was validated on the owner's Zorin/Noble host. The management container used to author these scripts has no root, QEMU or KVM and cannot perform the build. Use a full host/VM, not a restricted container. Root and private mount/PID namespaces are required for the bootstrap; disk partitioning happens inside libguestfs and never touches a host disk.

Use a checkout path containing only letters, digits, dots, underscores, slashes and hyphens, for example `~/vps-linux`. Paths with spaces/commas are rejected rather than interpolated into appliance/QEMU commands. Reserve at least 20 GiB free disk space and 4 GiB available RAM. These are conservative prerequisites, not measured resource usage. The published v0.2 image is 957,743,104 bytes (~914 MiB); full build time and peak disk use have not been recorded.

## Host dependencies (Ubuntu 24.04/Zorin Noble)

```sh
sudo apt-get update
sudo apt-get install -y \
  mmdebstrap libguestfs-tools qemu-utils qemu-system-x86 ovmf \
  cloud-image-utils busybox-static gnupg dosfstools e2fsprogs \
  python3 python3-yaml shellcheck minisign git util-linux build-essential dpkg-dev
```

Debian 13 uses the same package names. A readable installed host kernel is required by libguestfs/supermin. Run `sudo libguestfs-test-tool` if its appliance cannot start. KVM is optional; libguestfs and the test runner can use software emulation, which is slower. Secure Boot must be off for this initial unsigned GRUB build.

## Build

```sh
git switch feature/vpsctl-0.1
# Install rustup separately; compile as your ordinary user, not under sudo.
rustup toolchain install 1.99.0 --profile minimal --component rustfmt --component clippy
./vpsctl/scripts/package-deb.sh
python3 scripts/vpsctl_package.py --source . --json
./tests/static-checks.sh
sudo ./build.sh --check
mkdir -p output
sudo ./build.sh
```

`--check` validates the prepared vpsctl package (exact clean source commit/version, allowed payload, no maintainer hooks), host tools, privileges, architecture, OS, disk space, path safety and namespace support without creating an image. There are no options to specify block devices or overwrite existing artifacts. `build.sh` creates a unique private work directory under `output/`, uses a build lock and publishes a complete bundle by directory rename. Stages run in separate process groups; interruption terminates the active stage before cleanup. Its exit trap removes only its marked work directory, refusing to recursively remove a mounted, symlinked or unmarked path.

If the process is terminated with SIGKILL or the machine loses power, no shell trap can run. Private namespace mounts disappear with their processes; an incomplete hidden work directory may remain. Verify no build process is still running before manually removing that specific directory. Never run recursive deletion on a mounted rootfs or a physical disk.

## Outputs

A successful build prints a path such as:

```text
output/vps-linux-v0.4-<UTC timestamp>-<commit>/
  vps-linux-v0.5.qcow2
  vps-linux-v0.4.qcow2.sha256
  vpsctl_0.4.0_amd64.deb
  packages.tsv
  build.json
  sbom.spdx.json
  SHA256SUMS
  (optional) SHA256SUMS.minisig
```

`sbom.spdx.json` is an SPDX 2.3 document generated from `packages.tsv` (one package entry per installed Debian binary package, with purl references). `SHA256SUMS` covers the image, its checksum file, the manifest, `build.json` the SBOM and the included vpsctl package. Verify any bundle with `./scripts/verify-release.sh <bundle>`; add `--minisign-pubkey FILE` or `--cosign-bundle FILE` to check a signature. CI produces a keyless cosign `.sigstore.json` bundle instead of a local minisign signature.

The disk is an 8 GiB QCOW2 with GPT, a 512 MiB FAT EFI System Partition and ext4 root. Labels `VPS_EFI` and `VPS_ROOT` are used in fstab. Do not attach multiple clones with these same labels to one running guest. GRUB installs `EFI/BOOT/BOOTX64.EFI` via `--removable --no-nvram`; no host UEFI entry is written. The kernel has virtio drivers in its initramfs, and logs to ttyS0.

The bundle is read-only by file mode as a guard against accidents, not cryptographically immutable. Always test overlays, not the backing artifact. The build performs `qemu-img check`, format/size/backing-file validation and SHA256 generation/verification. It does **not** claim boot success; run [the smoke test](testing.md).

## Package inputs and repeatability

The first-party vpsctl package is built from this clean checkout with locked Rust dependencies. Its snapshot is validated again before installation via dpkg; its source/hash are recorded in build.json and it is included in the manifest/SBOM. No Rust compiler is installed in the guest. Rebuild the package after each commit; mismatching or dirty-package provenance is rejected.

Debian dependencies use only official `trixie`, `trixie-updates` and `trixie-security` main repositories are used. Vendored [public archive keys](../configs/apt/README.md) provide the initial trust roots; APT signature and artifact-checksum verification stays enabled. No third-party Docker repository is used, and no proxy settings/credentials are stored in the guest.

The goal is a repeatable procedure; it produced the published v0.2 image. Packages are not version-locked or snapshot-pinned. Apt archives move; filesystem UUIDs, build timestamps and metadata vary. **Byte-for-byte reproducibility has not been implemented or verified.** `packages.tsv` records exact installed versions; `build.json` records the source commit, dirty status and digests. These are audit records, not enough to reconstruct packages that disappear from mirrors.

## Troubleshooting

- Missing command/root/namespace error: install the prerequisites or use a full supported host. Do not weaken the checks or try a physical disk.
- APT signature error: check the clock, repository availability and Debian key-rotation notices. Do not use `trusted=yes`, `--no-check-gpg` or disable TLS.
- libguestfs appliance error: run `sudo libguestfs-test-tool`, check available RAM, host kernel and KVM permissions. Use `LIBGUESTFS_BACKEND=direct`; this builder sets it itself.
- Compose version/interface failure: the build fails before packaging. Keep the Debian V2 package and inspect the actual package version; do not silently substitute Compose V1.
- Failed bootstrap/image stages: the unpublished work directory is removed; keep terminal output for diagnosis. Do not paste credentials or the full process environment.

## Versioning and releases

The released v0.2 artifact was built from clean commit `7d0ec202786edc037816a946146f1b40912515eb`; its image SHA256 is recorded in the release and in `docs/validation.md`. Do not rebuild changed source under the published `0.2` label.

After that release, `VERSION` selects `0.3-dev` for the next development cycle. Stable candidates (a version without the `-dev` suffix) require a clean tracked/untracked source tree before building and fail packaging if the source revision or working tree changes during the build. Generated ignored images and keys are not source dirtiness. The final guest marker, issue text, artifact name and metadata all derive from this one file.

Run `./tests/release-check.sh` after a successful versioned build. It selects the latest image matching `VERSION`, checks that its metadata records a clean build and runs the extended two-instance acceptance harness. It never substitutes an image for a different version. Repeat acceptance for every new artifact even if a prior image passed.

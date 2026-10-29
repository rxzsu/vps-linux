# Reproducibility status

Byte-for-byte reproducibility is **not claimed** for any published release. This document records what is already deterministic, what is not, and the milestone path. `docs/releasing.md` repeats the disclaimer so no reader mistakes repeatable builds for reproducible ones.

## Terminology

- **Repeatable**: the same source, on the same host, produces a working image again. Required and verified by the release gates.
- **Reproducible**: the same source produces **byte-identical** artifacts on different hosts and at different times. This is the milestone.

## Already deterministic today

- **vpsctl Debian package** (`vpsctl/scripts/package-deb.sh`): builds with `SOURCE_DATE_EPOCH` pinned to the vpsctl tree's last commit, `gzip -n` for the man page, and `dpkg-deb --uniform-compression -Zxz -z6`, which normalizes file metadata and compression across builds of the same inputs.
- **SPDX SBOM** (`scripts/sbom.py`): generated deterministically from the recorded package manifest (sorted entries, canonical JSON hashing).
- **Bundle manifest** (`SHA256SUMS`): covers every published artifact, so any nondeterminism is at least *detected and visible* in build.json history.
- **Source binding**: `build.json` records the exact commit, dirty state, vpsctl version and package SHA256, so two bundles can be compared against the same source identity.

## Known nondeterminism in the image path

1. **Bootstrap package set**: mmdebstrap installs from the live Debian mirror at build time. Without a pinned mirror snapshot (e.g. `snapshot.debian.org`) the package versions differ between builds.
2. **Rootfs metadata**: file ownership, mtimes and inode ordering inside the rootfs are not currently normalized (`SOURCE_DATE_EPOCH` is exported by `build.sh`, but consumers inside the bootstrap do not uniformly honor it yet).
3. **ext4/GPT layout**: libguestfs allocation order, UUIDs and filesystem superblock timestamps are not pinned. Partition/filesystem UUIDs are generated fresh per build by design.
4. **initramfs/GRUB**: regenerated inside the guest at build time; their contents embed timestamps and host-dependent ordering.
5. **QCOW2 layer**: allocation and cluster reuse in the converted standalone image depends on the input stream.

## Milestone path

Ordered by leverage; each step is independently verifiable:

1. **Pin the mirror**: bootstrap from a `snapshot.debian.org` timestamp recorded in `build.json` (largest single source of divergence).
2. **Normalize rootfs metadata**: enforce `SOURCE_DATE_EPOCH` mtimes and sorted file ordering in the configured rootfs before image creation.
3. **Pin UUIDs/timestamps in the disk layer**: derive partition/filesystem UUIDs from the source commit where the format allows; zero or fix superblock time fields.
4. **Two-host comparison harness**: a script that builds twice (two hosts or a clean container), diffs `SHA256SUMS`, and reports the first diverging artifact with per-file comparison. Even partial divergence reports are useful evidence.
5. Only after all bundle artifacts match across hosts: publish the reproducibility claim, and keep it enforced by CI.

Steps 1–2 also improve **auditability** (a known package snapshot) even before the full claim becomes true.

## Honest limits

A reproducibility claim only becomes meaningful when an independent party can reproduce it. Until step 5, the trust anchors remain `SHA256SUMS`, the cosign keyless bundle, GitHub artifact attestations and the recorded source commit — see `docs/releasing.md`.

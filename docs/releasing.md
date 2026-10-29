# Release gate

v0.1 and v0.2 are published and immutable. Do not replace, retag or relabel their QCOW2/checksum assets. v0.2 was published from clean source `7d0ec202786edc037816a946146f1b40912515eb`; its acceptance and publication evidence is in [validation.md](validation.md).

The next candidate uses image `VERSION` = `0.5` and vpsctl `0.5.0`. See [v0.5 integration](v0.5.md). First build/test locally with publication disabled; publication requires a fresh fully tested main run with publish_release. Stable `v0.4` was published on 2026-10-28 from `b5bc3c5301226211dfb2c457a477c3eed8f75876`; the next stable version must be a new label. The release includes the source-bound vpsctl Debian package and verifies its uploaded bytes as well as the image. Earlier tags/prereleases remain unchanged. Never reuse a published stable version label for changed sources.

Before considering the next stable release:

1. Review the source diff, trust roots and source commit; build from a clean checkout on the developer's Zorin/Ubuntu 24.04 host.
2. Keep the complete candidate bundle and verify it with `./scripts/verify-release.sh <bundle>` (checksums and SPDX SBOM). Sign `SHA256SUMS` before publication: CI uses keyless cosign; a local build may use `VPS_LINUX_SIGNING_KEY` + minisign. Publish the SBOM and signature next to the image.
3. Run the automated two-instance smoke suite successfully against disposable overlays. Keep exact command, exit status, source commit, package manifest, firmware version and acceleration used.
4. On the connected developer host verify actual NTP synchronization, Docker hello-world, an HTTP container workload and absence of failed units. Test shutdown/reboot and another fresh instance.
5. Investigate every unexplained failure; do not mark unrun/expected checks as passed.
6. Re-run build/acceptance if code, package inputs or configuration change. Review configuration cleanup and ensure no machine IDs, host keys, accounts, authorized keys, test credentials or proxy secrets remain in the candidate.
7. Record build time, peak disk usage and final artifact size with the observed environment. v0.2 recorded only the published artifact size.
8. Obtain the repository owner's approval before merging or creating a tag/release. Version promotion must update `VERSION` and all metadata consistently; a stable version must be built from a clean tree.
9. Publish a **new** release with image, verified SHA256, `SHA256SUMS`, SPDX SBOM, signature (if policy requires it), source commit, package manifest, build metadata, supported firmware/datasource configuration and known limitations. Re-download and reverify published artifacts before announcing them. Never modify v0.1 or v0.2 assets.

## Verifying a published release

Beyond `SHA256SUMS` and the keyless cosign bundle, the publication job signs every bundle artifact (image, checksums, SBOM, package, metadata) with a keyless GitHub artifact attestation bound to this repository's workflow. Verify a downloaded file against the repository identity:

```sh
gh attestation verify <downloaded-file> --repo rxzsu/vps-linux
```

An attestation proves which workflow run produced the bytes; it does not prove boot acceptance — the acceptance evidence for each stable release stays in `docs/validation.md`.

The one-shot `scripts/publish-v0.2.sh` has already been used. It refuses to run while tag `v0.2` exists; keep it for provenance and do not force-overwrite the tag.

Byte-reproducibility is a separate project milestone requiring snapshot/version pins, deterministic filesystem/partition metadata, timestamp handling and independent rebuild comparison. Successful repeatable builds alone do not meet that claim. The current status, known nondeterminism sources and milestone path are tracked in [reproducibility.md](reproducibility.md).

## CI opt-in publication

The manual build workflow now supports `publish_release`, default false, from main only and only with build_and_boot/online_tests enabled. See [testing.md](testing.md#optional-automatic-tag-and-release) for the exact gate, development prerelease tags, artifact verification and stable promotion behavior. This automates the mechanics of the release gate; it does not let a failing or offline-only run publish. Never rerun the old v0.2 one-shot helper for v0.3.

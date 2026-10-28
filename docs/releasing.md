# Release gate

v0.1 and v0.2 are published and immutable. Do not replace, retag or relabel their QCOW2/checksum assets. v0.2 was published from clean source `7d0ec202786edc037816a946146f1b40912515eb`; its acceptance and publication evidence is in [validation.md](validation.md).

Current development is on `main` with `VERSION` = `0.3-dev`. Any change after the v0.2 tag belongs to the next version; bumping `VERSION` before a stable build is mandatory so a new artifact never reuses a published version label.

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

The one-shot `scripts/publish-v0.2.sh` has already been used. It refuses to run while tag `v0.2` exists; keep it for provenance and do not force-overwrite the tag.

Byte-reproducibility is a separate project milestone requiring snapshot/version pins, deterministic filesystem/partition metadata, timestamp handling and independent rebuild comparison. Successful repeatable builds alone do not meet that claim.

## CI opt-in publication

The manual build workflow now supports `publish_release`, default false, from main only and only with build_and_boot/online_tests enabled. See [testing.md](testing.md#optional-automatic-tag-and-release) for the exact gate, development prerelease tags, artifact verification and stable promotion behavior. This automates the mechanics of the release gate; it does not let a failing or offline-only run publish. Never rerun the old v0.2 one-shot helper for v0.3.

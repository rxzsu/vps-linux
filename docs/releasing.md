# Release gate

v0.1 is stable and immutable. Do not replace its QCOW2/checksum assets. v0.2 development remains on `feature/v0.2-build-system`; no release/tag/merge is authorized by merely creating the build scripts.

Before considering v0.2:

1. Review the source diff, trust roots and source commit; build from a clean checkout on the developer's Zorin/Ubuntu 24.04 host.
2. Keep the complete candidate bundle and verify its SHA256 from the bundle's working directory.
3. Run the automated two-instance smoke suite successfully against disposable overlays. Keep exact command, exit status, source commit, package manifest, firmware version and acceleration used.
4. On the connected developer host verify actual NTP synchronization, Docker hello-world, an HTTP container workload and absence of failed units. Test shutdown/reboot and another fresh instance.
5. Investigate every unexplained failure; do not mark unrun/expected checks as passed.
6. Re-run build/acceptance if code, package inputs or configuration change. Review configuration cleanup and ensure no machine IDs, host keys, accounts, authorized keys, test credentials or proxy secrets remain in the candidate.
7. Measure build time, peak disk usage and final artifact size and update documentation with the observed environment.
8. Obtain the repository owner's approval before merging or creating a tag/release. Version promotion must update the build version and metadata consistently; current scripts intentionally emit `0.2-dev`.
9. Publish a **new** release with image, verified SHA256, source commit, package manifest, build metadata, supported firmware/datasource configuration and known limitations. Re-download and reverify published artifacts before announcing them. Never modify v0.1 assets.

Byte-reproducibility is a separate project milestone requiring snapshot/version pins, deterministic filesystem/partition metadata, timestamp handling and independent rebuild comparison. Successful repeatable builds alone do not meet that claim.

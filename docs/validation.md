# v0.2 validation status

Authoring environment: managed Debian 13 x86_64 container, 2026-10-28. No root privileges, mmdebstrap, libguestfs tools, qemu-img, QEMU or KVM device are available. `./build.sh --check` correctly exits nonzero before creating image files and lists missing prerequisites. User namespaces alone outside the command sandbox do not supply a full privileged build host.

## Executed

- Bash syntax and ShellCheck 0.11.0 on all build/test shell scripts.
- 19 Python safety/configuration tests pass in the static-check job; the configuration subset also passes locally where host tools are available.
- Verified Debian Trixie InRelease signatures with the installed official Debian archive keyring and verified Packages.xz SHA256 against that signed release.
- Downloaded cloud-init `25.1.4-1+deb13u1`, docker-compose `2.26.1-4` and docker.io `26.1.5+dfsg1-9+deb13u1`; checked each artifact against the signed package index before inspecting/executing it.
- Inspected the actual cloud-init unit names and native Compose plugin paths. Executed the verified Compose binary: `2.26.1-4`, and the verified Debian Docker CLI with that plugin: `Docker Compose version 2.26.1-4`. Host plugin discovery used an explicit temporary plugin directory; the build still checks native guest discovery.
- Validated the example NoCloud user-data using the official cloud-init 25.1.4 schema command in isolated local tooling. This validates the example, not an image boot or the merged system configuration.

- Website production build and all 9 desktop/mobile/reduced-motion RU/EN browser tests passed after correcting v0.1 Compose/provisioning documentation. The later v0.2 content update builds successfully; its browser suite was not rerun in this environment because no Playwright browser was installed.

## Owner-reported Zorin validation — 2026-10-28

The owner supplied terminal output from the local Zorin/Noble host for candidate:
`output/vps-linux-v0.2-dev-20261028T164637Z-1782d8f8c69f/vps-linux-v0.2-dev.qcow2`.
These are owner-reported results, not VM executions in the managed authoring container.

- Build completed after applying the explicit Bash cleanup invocation, now committed in `fc89f71`. Kernel observed: `6.12.113+deb13-amd64`.
- GPT/EFI/ext4 population, initramfs/GRUB installation, QCOW2 integrity and generated SHA256 verification succeeded.
- Offline two-instance smoke passed: UEFI, Debian, NoCloud completion without errors, key-based SSH, effective SSH restrictions, sudo, Docker container execution, both Compose interfaces, network, ZRAM, active NTP service and no failed units.
- Extended `--release-check` passed: actual NTP synchronization, Docker Hub hello-world/nginx pulls, HTTP response, guest reboot with changed boot ID, restored HTTP service, NTP resynchronization and persistent machine-id/SSH host keys.
- Two independent instances had distinct machine IDs and host keys.

Owner-supplied development metadata binds those reported results to image SHA256 `a623923e001a6b67a8adb7d83f92c1e12a4cbcd11a2d3526529dc606c13be72d`, package-manifest SHA256 `8b51580062a8c568a224890bdf15ca35e910a6c2e2820459b013bc6a254252a7`, source `1782d8f8c69ff297e76a210d294423d3a07ebeb4` with `source_dirty: true` and build timestamp `2026-10-28T16:51:14.470097+00:00`. This evidence does not transfer automatically to the final stable-version artifact.

## Owner-reported final candidate acceptance

The owner supplied passing extended checks for `output/vps-linux-v0.2-20261028T170809Z-7d0ec202786e/vps-linux-v0.2.qcow2`, built from final-version source `7d0ec202786edc037816a946146f1b40912515eb`. The release-check wrapper had admitted version 0.2 with `source_dirty: false` before running the harness. Both independent boots and the online/reboot checks passed, including NTP sync, registry pulls, HTTP recovery, persistent reboot identities and no failed units.

## Publication — completed 2026-10-28

The GitHub release was published and its uploaded bundle was verified against the tested candidate:

- Release `v0.2` is public and marked latest, not a draft; tag `v0.2` points to `7d0ec202786edc037816a946146f1b40912515eb`.
- Uploaded image SHA256 is `c5db7d6edde16f566ec646735d9b41e4bdb22996014407a8fd338d79435d176c`, identical to the `.sha256` asset and to `image_sha256` in the uploaded `build.json`.
- Uploaded `build.json` records version `0.2`, `source_dirty: false` and the same source commit.
- Uploaded `packages.tsv` SHA256 is `8b51580062a8c568a224890bdf15ca35e910a6c2e2820459b013bc6a254252a7`, matching `package_manifest_sha256` in the metadata.
- `scripts/publish-v0.2.sh` created the draft, re-downloaded the image and checksum, compared its bytes, and only then published the release. The v0.1 release and its assets were not modified.

Publication is finished. The one-shot `scripts/publish-v0.2.sh` is retained for provenance and now refuses to run because tag `v0.2` exists; do not force-overwrite the tag or its assets.

## Remaining limitations

- The GitHub Actions static job has passed; the manual `workflow_dispatch` build-and-boot job has not been run. Independent byte-for-byte rebuild comparison remains unrun.
- Full build duration, peak disk use and exact host firmware/acceleration were not recorded. The published v0.2 image asset is 957,743,104 bytes (~914 MiB); bootstrap timing alone is not total build time.
- `boot_smoke_test: not_run` remains unchanged in the immutable build-time metadata; the later acceptance results are recorded separately here and in the release's `acceptance.json`.
- v0.1 remains the legacy manually assembled release; its published assets are immutable and unchanged.

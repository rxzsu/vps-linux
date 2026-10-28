# v0.2 first-iteration validation status

Authoring environment: managed Debian 13 x86_64 container, 2026-10-28. No root privileges, mmdebstrap, libguestfs tools, qemu-img, QEMU or KVM device are available. `./build.sh --check` correctly exits nonzero before creating image files and lists missing prerequisites. User namespaces alone outside the command sandbox do not supply a full privileged build host.

## Executed

- Bash syntax and ShellCheck 0.11.0 on all build/test shell scripts.
- 16 Python safety/configuration tests, all passed.
- Verified Debian Trixie InRelease signatures with the installed official Debian archive keyring and verified Packages.xz SHA256 against that signed release.
- Downloaded cloud-init `25.1.4-1+deb13u1`, docker-compose `2.26.1-4` and docker.io `26.1.5+dfsg1-9+deb13u1`; checked each artifact against the signed package index before inspecting/executing it.
- Inspected the actual cloud-init unit names and native Compose plugin paths. Executed the verified Compose binary: `2.26.1-4`, and the verified Debian Docker CLI with that plugin: `Docker Compose version 2.26.1-4`. Host plugin discovery used an explicit temporary plugin directory; the build still checks native guest discovery.
- Validated the example NoCloud user-data using the official cloud-init 25.1.4 schema command in isolated local tooling. This validates the example, not an image boot or the merged system configuration.

- Website production build and all 9 desktop/mobile/reduced-motion RU/EN browser tests passed after correcting v0.1 Compose/provisioning documentation.

## Owner-reported Zorin validation — 2026-10-28

The owner supplied terminal output from the local Zorin/Noble host for candidate:
`output/vps-linux-v0.2-dev-20261028T164637Z-1782d8f8c69f/vps-linux-v0.2-dev.qcow2`.
These are owner-reported results, not VM executions in the managed authoring container.

- Build completed after applying the explicit Bash cleanup invocation, now committed in `fc89f71`. Kernel observed: `6.12.113+deb13-amd64`.
- GPT/EFI/ext4 population, initramfs/GRUB installation, QCOW2 integrity and generated SHA256 verification succeeded.
- Offline two-instance smoke passed: UEFI, Debian, NoCloud completion without errors, key-based SSH, effective SSH restrictions, sudo, Docker container execution, both Compose interfaces, network, ZRAM, active NTP service and no failed units.
- Extended `--release-check` passed: actual NTP synchronization, Docker Hub hello-world/nginx pulls, HTTP response, guest reboot with changed boot ID, restored HTTP service, NTP resynchronization and persistent machine-id/SSH host keys.
- Two independent instances had distinct machine IDs and host keys.

## Remaining release preparation

- Inspect the candidate's original build.json, checksum and package manifest to bind reported checks to the exact artifact; these files and QCOW2 currently remain on the owner's host.
- The tested artifact and current builder identify as `0.2-dev`. A stable `0.2` build must use consistent version markers/metadata and receive acceptance testing after promotion; do not silently rename/relabel the existing immutable candidate.
- Preserve exact source provenance, including the local Bash-launch patch applied on top of `1782d8f`; a clean release source revision still needs to be selected.
- Full build duration, peak disk use, exact host firmware/acceleration and final file size were not supplied. Bootstrap timing alone is not total build time.
- GitHub Actions manual integration workflow remains unrun; independent byte-for-byte rebuild comparison remains unrun.
- No v0.2 tag, merge, uploaded release asset or public release has been created by this task.

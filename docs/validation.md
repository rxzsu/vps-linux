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

## Not run / release blockers

- Full mmdebstrap bootstrap and package installation in the intended chroot.
- Actual GPT/filesystem creation, initramfs/GRUB installation and QCOW2 packaging.
- QEMU integrity checks and UEFI boot of a newly built v0.2 candidate.
- Two-instance cloud-init, SSH, Docker, ZRAM, NTP-service, failed-unit and identity-isolation smoke tests against that candidate.
- Actual NTP synchronization, external registry/HTTP workload tests, reboot and developer's Zorin-host validation.
- GitHub Actions manual integration workflow.

These are not passing checks and do not establish a working/released v0.2 image. The implementation is prepared for review and real-host validation; fixes may still be needed when the first integration run supplies evidence.

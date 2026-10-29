# Security policy

## Supported versions

| Version | Status |
| --- | --- |
| v0.2 (stable release) | Supported: security-relevant reports are accepted |
| v0.4 candidate (`main` / feature branch) | Supported: reports are accepted, fixes land before publication |
| v0.1, older tags | Not supported; assets remain frozen for provenance |

## Reporting a vulnerability

Use GitHub's **private vulnerability reporting** on the `rxzsu/vps-linux` repository (Security → Report a vulnerability). Do not open a public issue for anything that could be exploited.

Include: affected component (`build.sh`, a `scripts/` stage, a `configs/` policy file, the image itself, or `vpsctl`), the source commit you inspected, and a reproduction or PoC. Reports are acknowledged and triaged before any coordinated disclosure timeline is agreed.

## In scope

- The build pipeline: host isolation, namespace/bootstrap safety, path and device handling (the "file-backed images only" guarantee), cleanup of guest state.
- Image policy: SSH hardening drop-ins, Docker daemon settings, journald/unattended-upgrades caps, cloud-init seed handling.
- `vpsctl`: the read-only guarantee (no writes, no privilege escalation), input validation, JSON/TUI output handling, and the source-bound Debian package payload.
- Release integrity: `SHA256SUMS`, SPDX SBOM, minisign/cosign signatures and GitHub artifact attestations.

## Out of scope

- QEMU/KVM, the Linux kernel, Debian itself, Docker or cloud-init upstream code; report those upstream. This project assembles and configures them.
- Hosting providers and hypervisors the image runs on.
- Attacks requiring control of the already-authenticated host administrator (`debian` user), which is root-equivalent by design.
- Boot without UEFI, Secure Boot and other explicitly documented compatibility boundaries in `docs/architecture.md`.

## Verifying distributed artifacts

Always verify a downloaded image against `SHA256SUMS` and, where available, the cosign bundle (`scripts/verify-release.sh`) or `gh attestation verify <file> --repo rxzsu/vps-linux` before booting it. See `docs/releasing.md`.

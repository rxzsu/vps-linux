# Roadmap

Direction only — nothing here is scheduled, and published releases never change retroactively. Compatibility boundaries and their rationale stay in [architecture.md](architecture.md); this file lists what could extend them and what the project deliberately does not do.

## Near term

- **Publish stable v0.4** with source-bound vpsctl 0.4.0 once the full image/VM acceptance passes ([v0.4 integration](v0.4.md)).
- **Scheduled CI validation**: a periodic `static-checks.sh` / `build.sh --check` run to catch drift in the live Debian repositories before a release attempt does.
- **vpsctl diagnostics depth**: structured Docker observations and fixture-backed firewall/nftables analysis before any policy "health" claims (as already noted in `vpsctl/README.md`).

## Mid term

- **Reproducibility milestones**: mirror snapshot pinning, rootfs metadata normalization, UUID/timestamp pinning and a two-build comparison harness ([reproducibility.md](reproducibility.md)).
- **More vpsctl subcommand coverage** (still read-only): storage/ZRAM observations, boot/journal health, richer JSON schema versioning.
- **Website**: a downloadable-artifacts table generated from release metadata instead of manual README editing, plus screenshot/demo refresh.

## Long term / under consideration

- **arm64 (AArch64) image** alongside amd64; requires libguestfs/UEFI validation on that architecture and a second acceptance matrix.
- **BIOS (legacy) boot path** — low priority; UEFI-only is a documented boundary.
- **Secure Boot**: signed boot chain (shim/SBAT or custom keys) — significant key-management burden; not attempted until the reproducibility work lands.
- **Additional cloud-init datasources** (currently NoCloud only): each provider needs its own acceptance evidence.
- **vpsctl mutation commands** (intentionally not implemented): only with typed validation, displayed plan, explicit confirmation, atomic writes and tested rollback, per `vpsctl/README.md`.

## Explicitly out of scope

- Becoming a from-scratch distribution; Debian remains the package/security base.
- Retroactive changes to v0.1/v0.2 assets.
- Replacing Debian's security model (unattended security-only upgrades stay capped and reboot-free by policy).

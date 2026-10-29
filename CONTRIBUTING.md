# Contributing

Thanks for looking at VPS Linux. The project has a few hard rules; everything else is normal open-source collaboration.

## Ground rules

- **Never modify published release assets.** v0.1/v0.2 tags and their artifacts are immutable provenance. Never rebuild changed sources under a previously published stable version label.
- **Stable candidates require a clean checkout.** `build.sh` refuses a dirty tree for non-`-dev` versions, and the vpsctl package records `X-Vpsctl-Source-Commit`/`X-Vpsctl-Source-Dirty`.
- **Scripts accept file-backed images only.** Nothing may target host physical disks, loop devices or NBD.
- **No secrets in the tree.** Test credentials, host keys, machine IDs, signing keys and generated artifacts are ignored and must never be committed.
- `vpsctl` stays read-only. Configuration mutation is out of scope without a typed validation/confirmation/rollback design (see `vpsctl/README.md`).

## Before opening a pull request

Run the checks that match the changed area; CI runs the same set:

```sh
# vpsctl (from vpsctl/)
cargo +1.99.0 fmt --all -- --check
cargo +1.99.0 clippy --locked --all-targets --all-features -- -D warnings
cargo +1.99.0 deny --locked check advisories bans licenses sources
cargo +1.99.0 test --locked
python3 -m unittest discover -s tests -p 'test_*.py'
./scripts/package-deb.sh && python3 tests/package_deb.py

# build system (repo root)
./tests/static-checks.sh          # needs shellcheck, minisign, qemu-img, python3-yaml
```

Tool prerequisites are listed in `docs/building.md` and `docs/testing.md`.

## Conventions

- One logical change per pull request; describe *what was validated and what was not* in the description. A build exit status is not boot verification.
- Keep the documentation honest: if a check did not run, say so. Do not mark unrun checks as passed.
- Update `docs/` when behavior changes (`architecture.md` is the policy reference; `docs/releasing.md` gates publication).
- Commits: short imperative subject, body explaining the why when it is not obvious.

## Areas

- Image/config changes: `configs/`, `scripts/`, `packages/base.txt` — explain the policy rationale; first-boot behavior must stay within `docs/architecture.md`.
- vpsctl: `vpsctl/` — MSRV is pinned at 1.99.0; keep JSON schemas backward compatible.
- Website: `website/` — Bun/Vue 3; see `website/README.md`.
- Docs only: welcome, and still state clearly what you changed.

## Reporting security issues

Do not open public issues for vulnerabilities. See [SECURITY.md](SECURITY.md).

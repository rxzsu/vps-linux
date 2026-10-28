# vpsctl 0.1.0 validation

Executed in the development environment: Debian 13 x86_64 container,
`rustc 1.99.0 (b940084d7 2026-09-28)`. All Cargo commands used the committed lock.

- `cargo +1.99.0 fmt --all -- --check`: passed.
- `cargo +1.99.0 clippy --locked --all-targets --all-features -- -D warnings`: passed.
- `cargo +1.99.0 test --locked --all-targets`: 9 unit and 4 CLI integration tests passed.
- `cargo +1.99.0 build --locked`: passed.
- `python3 tests/tui_pty.py`: 2 actual PTY UI/terminal-restoration tests passed.
- `cargo +1.99.0 build --locked --release`: passed.
- Release binary `status --json` and `info --json`: executed successfully, with
  actual host observations and null VPS Linux image version on the container.
- Existing repository `tests/static-checks.sh`: all 60 tests and shell checks passed.

No root, Docker daemon or VPS Linux VM was required for these checks. This does
not establish packaged Debian guest acceptance. The new GitHub Actions workflow
has been authored but was not observed running from this environment. The image
builder, image VERSION, published tags and release assets were not changed.

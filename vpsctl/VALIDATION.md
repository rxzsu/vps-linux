# vpsctl 0.4.0 validation

Executed on the development Debian 13 x86_64 container with
`rustc 1.99.0 (b940084d7 2026-09-28)`; dependencies were locked.

- `cargo +1.99.0 fmt --all -- --check`: passed.
- `cargo +1.99.0 clippy --locked --all-targets --all-features -- -D warnings`: passed.
- `cargo +1.99.0 test --locked --all-targets`: 13 unit + 6 CLI tests passed.
- `cargo +1.99.0 build --locked` and `--release`: passed.
- `python3 tests/tui_pty.py`: 2 tests passed (Network navigation, refresh, resize,
  q/Ctrl-C and termios restoration, using the real executable/PTY).
- Python packaging ABI tests: 2 passed; newer/unknown glibc floors rejected.
- `scripts/package-deb.sh`: amd64 GNU/Linux build and Debian package succeeded.
  Derived dependencies: libc6 >= 2.39, libgcc-s1 >= 4.2, coreutils.
  dpkg-shlibdeps emitted package-directory/usr-merge diversion warnings on this
  container; dependency scan exited successfully. No clean-VM install is claimed.
- `python3 tests/package_deb.py`: extracted payload/metadata/version test passed;
  no maintainer scripts, services/configuration or setuid permission found.
- ShellCheck on package script and workflow YAML parsing: passed.
- Existing image `tests/static-checks.sh`: all 66 tests and shell checks passed.
- Actual `doctor --online --json`: HTTPS HEAD to deb.debian.org verified through
  the configured environment; NSS resolution was unknown rather than healthy.

24 utility/terminal/package tests passed in total. No package installation, root
or Docker daemon was needed. The GitHub Actions package job was authored but not
observed executing here. Debian 13 guest installation/boot acceptance remains a
follow-up before image integration. Image integration now targets VPS Linux 0.4; published releases are unchanged. Guest acceptance code is included but has not executed in this environment.

Image integration adds 6 rootless package/bundle regression tests (included in
the 66 above), with real .deb and sparse QCOW2 fixtures. They verify provenance,
payload restrictions, checksum coverage and installed-version/SBOM coherence.
The final clean package is checked against the committed source before push.

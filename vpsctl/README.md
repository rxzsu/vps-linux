# vpsctl 0.1.0

A first-party, read-only control center for VPS Linux. Rust 2024, MSRV **1.99.0**,
Linux x86_64 / Debian 13. This utility has its own version; it is not yet included
in the VPS Linux image. The v0.3 image pipeline and existing releases are unchanged.

## Build and install

Install Rust with rustup from https://rustup.rs, then from this directory:

```sh
rustup toolchain install 1.99.0 --profile minimal --component rustfmt --component clippy
cargo +1.99.0 build --locked --release
./target/release/vpsctl --help
# Optional, explicit system-wide installation:
sudo install -m 0755 target/release/vpsctl /usr/local/bin/vpsctl
```

`Cargo.lock` pins the dependency graph. Use `--locked`; do not regenerate the lock
as part of a release. This is dependency repeatability, not a claim of identical
binary bytes. Compilation needs a C linker; on Debian install `build-essential`.
Runtime probes use Debian's `coreutils` (timeout/df), `iproute2`, systemd, OpenSSH
and optionally nftables. Missing helpers produce unavailable observations rather
than requiring installation or elevation. There is no daemon or background service.

## Commands

```sh
vpsctl                    # TUI; interactive stdin AND stdout required
vpsctl --help
vpsctl --version
vpsctl status             # CPU count/load, RAM, root disk, uptime, kernel, OS
vpsctl status --json
vpsctl info               # Utility version, VPS Linux version if installed, OS
vpsctl doctor             # Services, default route, resolver config, NTP
vpsctl security           # Effective default-context SSH policy, timers, firewall visibility
```

All four subcommands support `--json` and work without a terminal or root. Root
can make additional security observations readable, but is not automatically
requested. `sudo vpsctl` is supported when the administrator explicitly chooses it.

The TUI uses the same collectors and data structures as CLI commands. Left/right
or Tab/Shift-Tab changes sections; up/down scrolls; `r` refreshes; `q`, Esc or
Ctrl-C exits. Resizing is supported. Observations are collected on entry/refresh,
not continuously. Terminal modes are restored on normal exit, errors and Rust
unwinding; SIGKILL cannot be handled. Each helper has a 4-second deadline plus
1-second kill grace. Refresh is synchronous, so unavailable helpers can delay
key handling until the bounded probes finish.

## JSON and exit codes

JSON is a single object on stdout, with `schema_version: 1`, no ANSI sequences,
no progress output and no raw helper stderr. Missing scalar information is `null`;
missing OS fields are omitted from `info.os`. Sizes use bytes, uptime uses seconds,
load is the Linux 1/5/15-minute load average, CPU count is online logical CPUs.
`memory_available_bytes` is Linux MemAvailable, not a derived estimate.

`doctor` and `security` produce:

```json
{"schema_version":1,"section":"doctor","checks":[{"id":"ntp_sync","level":"ok","summary":"Clock synchronized"}]}
```

This is an abbreviated example, not a claim about the current host. Check IDs
are stable in schema 1; consumers should accept additional fields/checks. Levels:

- `ok`: the specifically described observation was verified.
- `warning`: inactive/transitional service or missing expected configuration.
- `fail`: failed service or effective SSH setting contrary to VPS Linux policy.
- `unknown`: missing tool/data, denied access or a condition not verified by MVP.

Exit 0: successful status/info output, or all diagnostic checks are OK.
Exit 1: at least one failed diagnostic (takes precedence over unknown/warning).
Exit 2: incomplete/warning diagnostics, usage error, noninteractive TUI, or I/O error.
Status/info exit 0 does not certify a healthy system: inspect null fields.
Because the MVP explicitly reports coverage gaps, doctor/security commonly exit 2.
Human summaries may change; automation should use JSON IDs/levels, not parse prose.

## Security and limitations

No configuration writes, sudo calls, repairs, container execution or network
changes are performed. Fixed absolute helper paths and argument arrays are used,
without a shell or PATH lookup; helper output and file reads are capped at 256 KiB.
No credentials, private keys, full environment, raw firewall rules or raw service
stderr are printed. Human/TUI output replaces host control characters; JSON uses
standard escaping. No Docker API socket connection or external network request
is made. A running Docker service does not prove container/registry health.

DNS configuration and default-route presence are checked, **not** successful DNS
resolution or Internet connectivity. SSH `sshd -T` checks its default context;
Match conditions for a particular user/address are explicitly unverified. A
readable nftables ruleset does not establish a secure ingress policy; firewall
assessment remains unknown. Timers do not prove current packages or effective
unattended-upgrade origins. QEMU Guest Agent may legitimately be inactive where
no virtio agent channel exists. An unsupported/container host is handled through
unavailable/unknown observations; there is no assumption that it is VPS Linux.
Build commit/image SHA are not guessed: the image bundle holds that metadata;
the current image installs only `/usr/share/vps-linux/version` and packages.tsv.

## Tests

Run from `vpsctl/`, on Linux with Python 3 for PTY tests:

```sh
cargo +1.99.0 fmt --all -- --check
cargo +1.99.0 clippy --locked --all-targets --all-features -- -D warnings
cargo +1.99.0 test --locked --all-targets
cargo +1.99.0 build --locked
python3 tests/tui_pty.py
cargo +1.99.0 build --locked --release
```

Unit tests cover malformed/missing information and classifications. CLI tests
check actual executable output, JSON, help/version, usage and noninteractive
behavior without root or Docker. PTY tests exercise the actual terminal UI,
navigation, refresh, resize, Ctrl-C and termios restoration. A separate
`Validate vpsctl` workflow runs on Rust 1.99.0 and caches Cargo downloads/builds.
Full Debian 13 guest verification and distro packaging remain follow-up work.

## Future image integration and v0.2.0

Build a versioned `.deb` outside the guest with the pinned Rust toolchain and lock,
install under `/usr/bin/vpsctl`, and add it to a future image only after checking
its Debian 13 runtime ABI, package manifest/SBOM and VM smoke tests. Do not insert
Rust or development tools into the server image. Keep this change separate from
the v0.3 release; no packaging hook is enabled by this MVP.

Next: explicit opt-in DNS/connectivity probes, structured Docker health via an
approved access model, effective APT origin assessment, and context-aware SSH/
firewall diagnostics. Add fixture-based Debian 13 guest acceptance before shipping.
Networking/storage/settings TUI sections should arrive with their actual services,
not empty placeholders. Future mutations need typed validated inputs, a displayed
plan and explicit confirmation, atomic updates where possible, backups and tested
rollback/recovery (especially when an SSH connection could be lost). There are
no privileged mutation features in 0.1.0.

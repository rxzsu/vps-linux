# vpsctl 0.4.0

A first-party, read-only VPS Linux control center. Rust 2024, MSRV **1.99.0**,
Linux x86_64 / Debian 13. Utility versioning is separate from the image.
It is included in the VPS Linux v0.4 candidate as a validated Debian package. Existing published images are unchanged.

## Build, install and package

Install Rust with rustup from https://rustup.rs. From `vpsctl/`:

```sh
rustup toolchain install 1.99.0 --profile minimal --component rustfmt --component clippy
cargo +1.99.0 build --locked --release
./target/release/vpsctl --help
# Explicit optional installation:
sudo install -m 0755 target/release/vpsctl /usr/local/bin/vpsctl
```

Keep `Cargo.lock` pinned; `--locked` prevents dependency changes during release
builds. This is dependency repeatability, not a universal identical-binary claim.
Compilation needs a C linker (`build-essential` on Debian).

Build a versioned amd64 Debian package without root:

```sh
# Packaging prerequisites: dpkg-dev, python3, build-essential, Rust, Git.
./scripts/package-deb.sh
python3 tests/package_deb.py
# Optional system installation, only when you explicitly want it:
sudo apt install ./dist/vpsctl_0.4.0_amd64.deb
```

Packaging compiles the explicit `x86_64-unknown-linux-gnu` target with Rust 1.99.0.
`dpkg-shlibdeps` derives actual library requirements, and an ABI gate rejects a
glibc floor newer than Debian 13's 2.41. Build on Debian 13 or with a compatible
sysroot if a future Ubuntu runner exceeds this floor. The package installs only
`/usr/bin/vpsctl` and documentation, with root ownership and a non-setuid binary.
There are no maintainer scripts, configuration files or systemd units. Packaging
never installs the package or invokes sudo. `SOURCE_DATE_EPOCH` defaults to the
latest Git commit timestamp affecting this directory; use a clean committed tree
for distribution. CI uploads the package as an artifact, not a GitHub release.

Runtime helpers: coreutils (`timeout`, `df`), iproute2, systemd, OpenSSH, APT;
nftables and curl are optional. Missing tools/permissions give unknown results.
No Rust runtime, background service or running Docker daemon is required.

## Commands

```sh
vpsctl                     # TUI; interactive stdin AND stdout required
vpsctl --help
vpsctl --version
vpsctl status --json       # Online CPUs, load, RAM, root disk, uptime/kernel/OS
vpsctl info                # Utility/OS/VPS Linux version, where installed
vpsctl network --json      # Local interface state and typed IP addresses
vpsctl doctor              # Offline services, route, resolver config, NTP checks
vpsctl doctor --online     # Explicit outbound resolution and HTTPS HEAD probe
vpsctl doctor --online --dns-name example.com --json
vpsctl security --json     # SSH default context, effective APT policy, timers
```

Each subcommand supports `--json`. Ordinary commands work without root and without
a terminal. No-argument invocation with redirected stdin/stdout exits promptly
with instructions. Root can make some security observations readable; privileges
are never automatically elevated. `sudo vpsctl` remains an explicit admin choice.

For SSH Match evaluation, supply a **complete** connection context:

```sh
vpsctl security --json \
  --ssh-user debian --ssh-address 192.0.2.10 --ssh-host client.example \
  --ssh-local-address 192.0.2.20 --ssh-local-port 22
```

The five context options must be provided together. Addresses/port are typed;
user/host reject context separators and invalid inputs. This runs `sshd -T -C`
with fixed arguments, never a shell. Results cover that supplied context only;
they are not a certificate that every possible SSH connection is secure.

The effective APT dump is compared with the exact VPS Linux security-only origin
pattern, no extra Allowed-Origins, explicit disabled automatic reboots, and a
daily unattended-upgrade schedule. Nonmatching origins are a warning, not a claim
that arbitrary custom distributions are insecure. Timers and configuration do
not prove package freshness or a successful recent installation.

## TUI and output

Sections: Status, Info, Doctor, Security, Network. Left/right or Tab/Shift-Tab
switches; up/down scrolls; `r` refreshes; `q`, Esc and Ctrl-C exit. Resizing works.
CLI/TUI share collectors and result types. The TUI never initiates online probes.
Refresh is synchronous, so unavailable helpers may delay key handling for a few
seconds. Each helper is limited to 4 seconds plus a 1-second kill grace.
Terminal modes restore on normal exit, errors and Rust unwinding; SIGKILL cannot
be handled. Data refreshes on navigation/request, not continuously.

JSON is one stdout object with `schema_version: 1`, no ANSI/progress output or raw
helper stderr. Unavailable scalar values are `null`; missing OS fields are omitted
from `info.os`. Bytes/seconds are explicit in field names; load is the 1/5/15-minute
Linux load average. `network.interfaces` contains only interface names, link states
and IP/prefix records, not arbitrary fields from helper responses.

Diagnostic shape (abbreviated example, not a host health claim):

```json
{"schema_version":1,"section":"doctor","checks":[{"id":"ntp_sync","level":"ok","summary":"Clock synchronized"}]}
```

IDs are stable within schema 1. Accept extra fields/check IDs. Levels:

- `ok`: the specifically described observation was verified.
- `warning`: inactive/transitional service or a policy/configuration discrepancy.
- `fail`: failed service or effective SSH setting contrary to VPS Linux policy.
- `unknown`: missing data/tool, denied access, probe failure or unverified condition.

Exit 0: successful status/info/network output, or all diagnostics OK.
Exit 1: at least one failed diagnostic (takes precedence over unknown/warning).
Exit 2: incomplete/warning diagnostics, usage, noninteractive TUI or I/O error.
A successful status/info/network command does not certify host health; inspect
nulls. Coverage gaps commonly make doctor/security exit 2. Parse JSON IDs/levels,
not human prose. Existing schema-1 commands/fields remain compatible. `info.utility_package_source_commit` reports the installed package source commit only when its version matches this utility, or null if unavailable.

## Safety and limits

No configuration writes, repair commands, sudo calls, container execution, Docker
socket connection or network changes. Fixed absolute helpers and argument arrays;
no shell or PATH search. Files/stdout/stderr are capped at 256 KiB. Warnings on
stderr make a probe unknown (APT warnings can indicate unreadable configuration).
APT_CONFIG and DBus bus-address overrides are ignored to inspect system defaults.
No credentials, private keys, full environment, raw firewall rules or helper stderr
are printed. Human/TUI output strips controls; JSON uses standard escaping.

Offline doctor/network/TUI make no external network requests. `doctor --online`
explicitly permits NSS resolution of the selected hostname and a certificate-
verified HTTPS HEAD to `https://deb.debian.org/`. Curl user configuration is
disabled; configured environment proxies and CA trust are retained. DNS results
may come from hosts/cache/NSS, so success is not claimed as a direct DNS query.
A probe failure is unknown: missing curl, proxy policy and offline networking
cannot be reliably distinguished here. No arbitrary URL, credentials or payload
can be supplied. The hostname option is rejected without `--online`.

Firewall assessment remains unknown even if nftables is readable; the application
does not guess effective ingress policy. A running Docker service does not prove
API/container/registry health. QEMU Agent may be inactive without a virtio channel.
Unsupported/container hosts produce unavailable/unknown values instead of being
assumed to be VPS Linux. Image commit/checksum are not guessed: current images
install a version file, while detailed metadata is in the distributed bundle.

## Validation and follow-up

```sh
cargo +1.99.0 fmt --all -- --check
cargo +1.99.0 clippy --locked --all-targets --all-features -- -D warnings
cargo +1.99.0 test --locked --all-targets
cargo +1.99.0 build --locked
python3 tests/tui_pty.py
python3 -m unittest discover -s tests -p 'test_*.py'
cargo +1.99.0 build --locked --release
./scripts/package-deb.sh
python3 tests/package_deb.py
```

The separate `Validate vpsctl` CI runs on the exact MSRV, caches Cargo downloads/
builds and uploads the `.deb`. See [actual validation](VALIDATION.md). PTY tests
exercise navigation including Network, refresh, resize and terminal restoration.
Package tests inspect/extract without installing; they do not prove clean-guest
installation. The image smoke harness now runs `tests/verify-vpsctl-guest.py` for both fresh guests and after reboot; actual full VM execution must still pass before publication.

Next: execute the integrated v0.4 image/guest acceptance, including non-root CLI, effective security policy and TUI restoration. Rust build tools remain outside the server image. Add structured Docker observations and fixture-backed
firewall analysis before declaring policy health. Future configuration mutations
need typed validation, a displayed plan, explicit confirmation, backups, atomic
updates where feasible and tested remote-safe rollback. No mutations are implemented.

Image builds require a package from the exact clean checkout. Packaging records
X-Vpsctl-Source-Commit/Dirty; image preflight rejects stale/dirty provenance,
symlinks, privileged payloads, extra files and maintainer scripts. Run packaging
as your ordinary user after committing changes.

#!/usr/bin/env bash
# Build a package as the current user; never install it or invoke sudo.
set -Eeuo pipefail
umask 022
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
for tool in cargo python3 dpkg-deb git install; do
    command -v "$tool" >/dev/null || { echo "Missing packaging tool: $tool" >&2; exit 1; }
done
version=$(python3 -c 'import tomllib; print(tomllib.load(open("Cargo.toml", "rb"))["package"]["version"])')
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Invalid package version' >&2; exit 1; }
source_commit=$(git -c safe.directory="$project/.." rev-parse HEAD)
source_dirty=false
[[ -z $(git -c safe.directory="$project/.." status --porcelain --untracked-files=normal) ]] || source_dirty=true
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git log -1 --format=%ct -- .)}
[[ $SOURCE_DATE_EPOCH =~ ^[0-9]+$ ]] || { echo 'Invalid SOURCE_DATE_EPOCH' >&2; exit 1; }
cargo +1.99.0 build --locked --release --target x86_64-unknown-linux-gnu
cargo +1.99.0 run --locked --release --bin vpsctl-docs -- target/x86_64-unknown-linux-gnu/release/docs
work=$(mktemp -d /tmp/vpsctl-deb.XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/debian/vpsctl/DEBIAN" dist
install -Dm755 target/x86_64-unknown-linux-gnu/release/vpsctl "$work/debian/vpsctl/usr/bin/vpsctl"
install -Dm644 README.md "$work/debian/vpsctl/usr/share/doc/vpsctl/README.md"
install -Dm644 ../LICENSE "$work/debian/vpsctl/usr/share/doc/vpsctl/copyright"
gzip -n -9 -c target/x86_64-unknown-linux-gnu/release/docs/vpsctl.1 > "$work/man.gz"
install -Dm644 "$work/man.gz" "$work/debian/vpsctl/usr/share/man/man1/vpsctl.1.gz"
install -Dm644 target/x86_64-unknown-linux-gnu/release/docs/vpsctl.bash \
    "$work/debian/vpsctl/usr/share/bash-completion/completions/vpsctl"
install -Dm644 target/x86_64-unknown-linux-gnu/release/docs/_vpsctl \
    "$work/debian/vpsctl/usr/share/zsh/vendor-completions/_vpsctl"
# dpkg-shlibdeps derives the glibc floor from the actual binary ABI. Do not
# assume a binary built on a newer runner works on Debian 13.
command -v dpkg-shlibdeps >/dev/null || { echo 'Install dpkg-dev for ABI dependency scanning' >&2; exit 1; }
mkdir -p "$work/debian"
printf 'Source: vpsctl\n\nPackage: vpsctl\nArchitecture: amd64\nDescription: VPS Linux read-only control center\n' > "$work/debian/control"
printf 'Package: vpsctl\nVersion: %s\nArchitecture: amd64\n' "$version" > "$work/debian/vpsctl/DEBIAN/control"
dependencies=$(cd "$work" && dpkg-shlibdeps -O -e debian/vpsctl/usr/bin/vpsctl | sed -n 's/^shlibs:Depends=//p')
[[ -n $dependencies ]] || { echo 'Could not derive shared-library dependencies' >&2; exit 1; }
python3 scripts/check-deb-abi.py "$dependencies"
cat > "$work/debian/vpsctl/DEBIAN/control" <<CONTROL
Package: vpsctl
Version: $version
Architecture: amd64
X-Vpsctl-Source-Commit: $source_commit
X-Vpsctl-Source-Dirty: $source_dirty
Maintainer: VPS Linux contributors <noreply@vps-linux.invalid>
Depends: $dependencies, coreutils
Recommends: iproute2, systemd, openssh-server, nftables, curl
Section: admin
Priority: optional
Description: Read-only VPS Linux control center
 Terminal UI and scriptable diagnostics. No configuration mutation or daemon.
CONTROL
chmod 755 "$work/debian/vpsctl/DEBIAN"
chmod 644 "$work/debian/vpsctl/DEBIAN/control"
dpkg-deb --root-owner-group --uniform-compression -Zxz -z6 --build "$work/debian/vpsctl" "dist/vpsctl_${version}_amd64.deb"

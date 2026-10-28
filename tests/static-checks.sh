#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$PROJECT_DIR"
for tool in shellcheck minisign qemu-img apt-config; do
    command -v "$tool" >/dev/null || { echo "Missing static/integrity test tool: $tool (see docs/testing.md)" >&2; exit 1; }
done
for file in build.sh scripts/*.sh tests/*.sh; do bash -n "$file"; done
shellcheck -x build.sh scripts/*.sh tests/*.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v

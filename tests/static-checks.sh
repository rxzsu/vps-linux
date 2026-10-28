#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$PROJECT_DIR"
command -v shellcheck >/dev/null || { echo 'Install shellcheck to run static checks.' >&2; exit 1; }
for file in build.sh scripts/*.sh tests/*.sh; do bash -n "$file"; done
shellcheck -x build.sh scripts/*.sh tests/*.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v

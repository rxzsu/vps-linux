#!/usr/bin/env bash
# Select only candidates matching VERSION; never silently select a different version.
set -Eeuo pipefail
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
[[ $# == 0 ]] || { echo 'Usage: ./tests/release-check.sh' >&2; exit 1; }
image=$(python3 - "$PROJECT_DIR" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
version = (root / 'VERSION').read_text().strip()
candidates = sorted((root / 'output').glob(f'vps-linux-v{version}-*/vps-linux-v{version}.qcow2'))
if not candidates:
    sys.exit('No final candidate found. Run sudo ./build.sh first.')
image = candidates[-1]
metadata = json.loads((image.parent / 'build.json').read_text())
if metadata.get('version') != version or metadata.get('source_dirty') is not False:
    sys.exit('Candidate metadata does not describe a clean final-version build.')
print(image)
PY
)
printf 'Testing final candidate: %s\n' "$image"
exec "$PROJECT_DIR/tests/smoke-test.sh" "$image" --release-check

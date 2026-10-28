#!/usr/bin/env bash
# Verify a built or downloaded bundle: checksums, SBOM integrity and, when
# supplied, a detached signature over SHA256SUMS.
#
# Usage: ./scripts/verify-release.sh BUNDLE_DIR
#          [--minisign-pubkey FILE] [--cosign-bundle FILE]
set -Eeuo pipefail
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
[[ $# -ge 1 ]] || { echo 'Usage: verify-release.sh BUNDLE_DIR [--minisign-pubkey FILE] [--cosign-bundle FILE]' >&2; exit 1; }
bundle=$(realpath -e -- "$1")
shift
minisign_key=''
cosign_bundle=''
while (( $# )); do
    case $1 in
        --minisign-pubkey) [[ $# -ge 2 ]] || { echo 'Missing key path' >&2; exit 1; }; minisign_key=$(realpath -e -- "$2"); shift 2 ;;
        --cosign-bundle) [[ $# -ge 2 ]] || { echo 'Missing bundle path' >&2; exit 1; }; cosign_bundle=$(realpath -e -- "$2"); shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done
[[ -d $bundle && ! -L $bundle ]] || { echo 'Bundle must be a real directory.' >&2; exit 1; }
for file in SHA256SUMS sbom.spdx.json build.json packages.tsv; do
    [[ -f $bundle/$file && ! -L $bundle/$file ]] || { echo "Missing bundle file: $file" >&2; exit 1; }
done
(cd "$bundle" && sha256sum -c SHA256SUMS)
python3 - "$bundle" "$PROJECT_DIR" <<'PY'
import json, pathlib, sys
bundle = pathlib.Path(sys.argv[1])
metadata = json.loads((bundle / 'build.json').read_text())
sbom = json.loads((bundle / 'sbom.spdx.json').read_text())
if sbom.get('spdxVersion') != 'SPDX-2.3':
    sys.exit('SBOM is not SPDX 2.3')
if not sbom.get('packages'):
    sys.exit('SBOM lists no packages')
image = bundle / f"vps-linux-v{metadata['version']}.qcow2"
if not image.is_file():
    sys.exit(f"Image missing: {image.name}")
if metadata['image_sha256'] not in (bundle / (image.name + '.sha256')).read_text():
    sys.exit('build.json image hash does not match the checksum file')
rows = [line for line in (bundle / 'packages.tsv').read_text().splitlines() if line]
if len(rows) != len(sbom['packages']):
    sys.exit(f"SBOM package count {len(sbom['packages'])} != manifest {len(rows)}")
print(f"SBOM/checksum metadata OK: {len(rows)} packages, image {image.name}")
PY
if [[ -n $minisign_key ]]; then
    command -v minisign >/dev/null || { echo 'minisign is required for --minisign-pubkey.' >&2; exit 1; }
    minisign -Vm "$bundle/SHA256SUMS" -p "$minisign_key"
fi
if [[ -n $cosign_bundle ]]; then
    command -v cosign >/dev/null || { echo 'cosign is required for --cosign-bundle.' >&2; exit 1; }
    cosign verify-blob "$bundle/SHA256SUMS" \
        --bundle "$cosign_bundle" \
        --certificate-identity-regexp '^https://github\.com/rxzsu/vps-linux/\.github/workflows/validate-build-system\.yml@refs/(heads|pull|workflows)/' \
        --certificate-oidc-issuer 'https://token.actions.githubusercontent.com'
fi
if [[ -z $minisign_key && -z $cosign_bundle ]]; then
    echo 'No signature supplied; checksums and SBOM were verified without a trust root.' >&2
fi
printf 'Verified bundle: %s\n' "$bundle"

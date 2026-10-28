#!/usr/bin/env bash
# Verify a built or downloaded bundle: checksums, SBOM integrity and, when
# supplied, a detached signature over SHA256SUMS.
#
# Usage: ./scripts/verify-release.sh BUNDLE_DIR
#          [--minisign-pubkey FILE] [--cosign-bundle FILE]
set -Eeuo pipefail
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
[[ $# -ge 1 ]] || { echo 'Usage: verify-release.sh BUNDLE_DIR [--minisign-pubkey FILE] [--cosign-bundle FILE]' >&2; exit 1; }
[[ -d $1 && ! -L $1 ]] || { echo 'Bundle must be a real directory.' >&2; exit 1; }
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
image=$(python3 "$PROJECT_DIR/scripts/verify-bundle.py" "$bundle")
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
command -v qemu-img >/dev/null || { echo 'qemu-img is required to verify image structure.' >&2; exit 1; }
qemu-img info --output=json "$image" | python3 "$PROJECT_DIR/scripts/check-image.py"
qemu-img check -f qcow2 "$image"
printf 'Verified bundle: %s\n' "$bundle"

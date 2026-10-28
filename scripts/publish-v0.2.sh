#!/usr/bin/env bash
# One-shot maintainer command used to publish v0.2 on 2026-10-28. Retained for provenance.
# It refuses to run once tag v0.2 exists, so it cannot overwrite the published release.
set -Eeuo pipefail
umask 077
if [[ ${1:-} == --help || ${1:-} == -h ]]; then
    printf 'Usage: ./scripts/publish-v0.2.sh\nRetained v0.2 publication helper. The release is already published; the tag is immutable.\n'; exit 0
fi
[[ $# == 0 ]] || { echo 'Use --help' >&2; exit 1; }
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
repo=rxzsu/vps-linux
tag=v0.2
commit=7d0ec202786edc037816a946146f1b40912515eb
bundle="$PROJECT_DIR/output/vps-linux-v0.2-20261028T170809Z-7d0ec202786e"
image="$bundle/vps-linux-v0.2.qcow2"
for tool in gh git python3 sha256sum qemu-img; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
[[ -f $image && ! -L $image ]] || { echo "Tested image not found: $image" >&2; exit 1; }
qemu-img check -f qcow2 "$image"
qemu-img info --output=json "$image" | python3 "$PROJECT_DIR/scripts/check-image.py"
(cd "$bundle" && sha256sum -c vps-linux-v0.2.qcow2.sha256)
python3 - "$bundle" "$commit" <<'PY'
import hashlib, json, pathlib, sys
bundle = pathlib.Path(sys.argv[1])
metadata = json.loads((bundle / 'build.json').read_text())
if metadata.get('version') != '0.2' or metadata.get('source_dirty') is not False or metadata.get('source_commit') != sys.argv[2]:
    sys.exit('Metadata does not match the clean final source that the owner tested')
checksum = (bundle / 'vps-linux-v0.2.qcow2.sha256').read_text().strip().split(maxsplit=1)
if len(checksum) != 2 or checksum[1] != 'vps-linux-v0.2.qcow2' or checksum[0] != metadata.get('image_sha256'):
    sys.exit('Image checksum and build metadata disagree')
if hashlib.sha256((bundle / 'packages.tsv').read_bytes()).hexdigest() != metadata.get('package_manifest_sha256'):
    sys.exit('Package manifest does not match build metadata')
PY
# Refuse to overwrite an existing tag/release or redirect it to a different commit.
existing=$(git -C "$PROJECT_DIR" ls-remote --tags origin refs/tags/v0.2 'refs/tags/v0.2^{}')
[[ -z $existing ]] || { echo 'v0.2 tag already exists; inspect it before continuing. Nothing overwritten.' >&2; exit 1; }
work=$(mktemp -d /tmp/vps-linux-publish.XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
cp "$PROJECT_DIR/docs/releases/v0.2.md" "$work/notes.md"
python3 - "$bundle/build.json" "$work" <<'PY'
import datetime, json, pathlib, sys
metadata = json.loads(pathlib.Path(sys.argv[1]).read_text())
work = pathlib.Path(sys.argv[2])
report = {
    'version': '0.2', 'source_commit': metadata['source_commit'],
    'image_sha256': metadata['image_sha256'],
    'evidence': 'Owner-provided Zorin terminal output for the exact named final candidate',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'result': 'passed',
    'checks': ['two independent UEFI boots', 'NoCloud and SSH policy', 'Docker and both Compose interfaces',
               'DHCP and ZRAM', 'distinct first-boot identities', 'NTP synchronized', 'Docker Hub pull',
               'HTTP workload', 'reboot and persistent identities', 'HTTP recovery and no failed units'],
    'independent_cloud_vm_execution': False,
}
(work / 'acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
with (work / 'notes.md').open('a') as stream:
    stream.write('\nSource commit: `' + metadata['source_commit'] + '`\n\nImage SHA256: `' + metadata['image_sha256'] + '`\n')
PY
echo 'Creating draft and uploading image, checksum, packages, metadata and acceptance record...'
gh release create "$tag" --repo "$repo" --target "$commit" --draft --title 'VPS Linux v0.2' \
    --notes-file "$work/notes.md" "$image" "$image.sha256" "$bundle/packages.tsv" "$bundle/build.json" "$work/acceptance.json"
echo 'Downloading the uploaded draft image to verify its bytes before publication...'
mkdir "$work/download"
gh release download "$tag" --repo "$repo" --dir "$work/download" \
    --pattern vps-linux-v0.2.qcow2 --pattern vps-linux-v0.2.qcow2.sha256
cmp "$image.sha256" "$work/download/vps-linux-v0.2.qcow2.sha256"
(cd "$work/download" && sha256sum -c vps-linux-v0.2.qcow2.sha256)
gh release edit "$tag" --repo "$repo" --draft=false --latest
echo 'Published: https://github.com/rxzsu/vps-linux/releases/tag/v0.2'

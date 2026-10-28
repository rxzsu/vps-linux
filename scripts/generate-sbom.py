#!/usr/bin/env python3
"""Generate a deterministic SPDX 2.3 JSON SBOM from the package manifest.

Usage:
    generate-sbom.py PACKAGES.tsv OUTPUT.spdx.json --version VERSION
                     --commit COMMIT [--created ISO8601]

The manifest is `dpkg-query -W` output: package name, tab, version. Package
names may carry an architecture qualifier (for example libc6:amd64).
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re

parser = argparse.ArgumentParser()
parser.add_argument('manifest', type=pathlib.Path)
parser.add_argument('output', type=pathlib.Path)
parser.add_argument('--version', required=True)
parser.add_argument('--commit', required=True)
parser.add_argument('--created')
args = parser.parse_args()

created = args.created or datetime.datetime.now(
    datetime.timezone.utc).isoformat(timespec='seconds')

packages = []
seen = set()
for line in args.manifest.read_text().splitlines():
    if not line.strip():
        continue
    name, version = line.split('\t', 1)
    arch = 'amd64'
    if ':' in name:
        name, arch = name.split(':', 1)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9+.-]*', name):
        raise SystemExit(f'Invalid package name in manifest: {name!r}')
    if not version.strip():
        raise SystemExit(f'Missing version for package: {name}')
    if name in seen:
        raise SystemExit(f'Duplicate package in manifest: {name}')
    seen.add(name)
    spdx_id = 'SPDXRef-Package-' + re.sub(r'[^A-Za-z0-9.-]', '-', name)
    packages.append({
        'SPDXID': spdx_id,
        'name': name,
        'versionInfo': version,
        'supplier': 'NOASSERTION',
        'downloadLocation': 'NOASSERTION',
        'filesAnalyzed': False,
        'licenseConcluded': 'NOASSERTION',
        'licenseDeclared': 'NOASSERTION',
        'copyrightText': 'NOASSERTION',
        'externalRefs': [{
            'referenceCategory': 'PACKAGE-MANAGER',
            'referenceType': 'purl',
            'referenceLocator': f'pkg:deb/debian/{name}@{version}?arch={arch}',
        }],
    })

manifest_bytes = args.manifest.read_bytes()
document = {
    'spdxVersion': 'SPDX-2.3',
    'dataLicense': 'CC0-1.0',
    'SPDXID': 'SPDXRef-DOCUMENT',
    'name': f'vps-linux-{args.version}',
    'documentNamespace': (
        'https://github.com/rxzsu/vps-linux/spdx/'
        f'{args.version}-{args.commit[:12]}'),
    'creationInfo': {
        'created': created,
        'creators': ['Tool: vps-linux-generate-sbom'],
    },
    'documentDescribes': [package['SPDXID'] for package in packages],
    'packages': packages,
    'annotations': [{
        'annotationDate': created,
        'annotationType': 'OTHER',
        'annotator': 'Tool: vps-linux-generate-sbom',
        'comment': (
            'Source package manifest sha256: '
            + hashlib.sha256(manifest_bytes).hexdigest()
            + f'; source commit: {args.commit}'),
    }],
}
args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n')
print(f'Wrote {len(packages)} packages to {args.output}')

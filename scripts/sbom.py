"""SPDX package identities and content-addressed document generation (stdlib only)."""
import datetime
import hashlib
import json
import re
from urllib.parse import quote


def parse_manifest(data):
    packages = []
    seen = set()
    for line in data.decode('utf-8').splitlines():
        if not line.strip():
            continue
        fields = line.split('\t')
        if len(fields) not in (2, 3):
            raise ValueError('Package manifest requires name, version and optional architecture')
        name, version = fields[:2]
        qualifier = None
        if ':' in name:
            name, qualifier = name.split(':', 1)
        arch = fields[2] if len(fields) == 3 else qualifier
        if qualifier and arch != qualifier:
            raise ValueError('Package architecture qualifier disagrees with manifest')
        if not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*', name) or not version.strip():
            raise ValueError('Invalid package name or empty version')
        if arch is not None and not re.fullmatch(r'[a-z0-9][a-z0-9-]*', arch):
            raise ValueError('Invalid package architecture')
        key = (name, arch)
        if key in seen:
            raise ValueError('Duplicate package/architecture in manifest')
        seen.add(key)
        vendor = 'vps-linux' if name == 'vpsctl' else 'debian'
        locator = f'pkg:deb/{vendor}/{quote(name, safe="")}@{quote(version, safe="")}'
        if arch is not None:
            locator += '?arch=' + arch
        packages.append({
            'SPDXID': 'SPDXRef-Package-' + (name + ':' + (arch or '')).encode().hex(),
            'name': name, 'versionInfo': version, 'supplier': 'NOASSERTION',
            'downloadLocation': 'NOASSERTION', 'filesAnalyzed': False,
            'licenseConcluded': 'NOASSERTION', 'licenseDeclared': 'NOASSERTION',
            'copyrightText': 'NOASSERTION',
            'externalRefs': [{'referenceCategory': 'PACKAGE-MANAGER', 'referenceType': 'purl',
                              'referenceLocator': locator}],
        })
    if not packages:
        raise ValueError('Empty package manifest')
    return sorted(packages, key=lambda package: package['SPDXID'])


def namespace(document):
    # Hash every document field except the namespace itself, avoiding a cycle.
    content = {key: value for key, value in document.items() if key != 'documentNamespace'}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return 'https://github.com/rxzsu/vps-linux/spdx/' + digest


def generate(data, version, commit, created):
    stamp = datetime.datetime.fromisoformat(created.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Creation timestamp must include a timezone')
    stamp = stamp.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    packages = parse_manifest(data)
    document = {
        'spdxVersion': 'SPDX-2.3', 'dataLicense': 'CC0-1.0', 'SPDXID': 'SPDXRef-DOCUMENT',
        'name': 'vps-linux-' + version,
        'creationInfo': {'created': stamp, 'creators': ['Tool: vps-linux-generate-sbom-1']},
        'documentDescribes': [package['SPDXID'] for package in packages], 'packages': packages,
        'annotations': [{'annotationDate': stamp, 'annotationType': 'OTHER',
                         'annotator': 'Tool: vps-linux-generate-sbom-1',
                         'comment': 'Source package manifest sha256: ' + hashlib.sha256(data).hexdigest()
                                    + '; source commit: ' + commit}],
    }
    document['documentNamespace'] = namespace(document)
    return document

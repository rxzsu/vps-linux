#!/usr/bin/env python3
"""Publish only a fully tested manual main-branch CI build; never overwrite a tag."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPOSITORY = 'rxzsu/vps-linux'
WORKFLOW = '.github/workflows/validate-build-system.yml'


def publication_plan(metadata, version, context):
    if context.get('GITHUB_EVENT_NAME') != 'workflow_dispatch' or context.get('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('Publication requires a manual main-branch workflow')
    if context.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('Unexpected publication repository')
    sha = context.get('GITHUB_SHA', '')
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Missing full workflow source SHA')
    if not re.fullmatch(r'[0-9]+\.[0-9]+(?:-dev)?', version):
        raise ValueError('Invalid release version')
    if metadata.get('version') != version or metadata.get('source_commit') != sha or metadata.get('source_dirty') is not False:
        raise ValueError('Build metadata must match the clean, exact workflow source')
    run, attempt = context.get('GITHUB_RUN_ID', ''), context.get('GITHUB_RUN_ATTEMPT', '')
    if not re.fullmatch(r'[1-9][0-9]*', run) or not re.fullmatch(r'[1-9][0-9]*', attempt):
        raise ValueError('Missing workflow run/attempt identity')
    prerelease = version.endswith('-dev')
    tag = f'v{version}.{run}.{attempt}' if prerelease else 'v' + version
    return {'tag': tag, 'prerelease': prerelease, 'latest': not prerelease, 'commit': sha,
            'version': version, 'run_url': f'https://github.com/{REPOSITORY}/actions/runs/{run}',
            'identity': f'https://github.com/{REPOSITORY}/{WORKFLOW}@refs/heads/main'}


def api(path, token, payload=None, missing_ok=False):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request('https://api.github.com/repos/' + REPOSITORY + '/' + path, data=data,
                      headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                               'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 404 and missing_ok and payload is None:
            return None
        raise RuntimeError(f'GitHub API HTTP {error.code} for {path}') from error


def require_absent(plan, token, query=api):
    tag = quote(plan['tag'], safe='')
    if query('git/ref/tags/' + tag, token, missing_ok=True) is not None:
        raise ValueError('Tag already exists; refusing to overwrite it')
    if query('releases/tags/' + tag, token, missing_ok=True) is not None:
        raise ValueError('Release already exists; refusing to overwrite it')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    bundle = args.bundle.resolve()
    metadata = json.loads((bundle / 'build.json').read_text())
    plan = publication_plan(metadata, (source / 'VERSION').read_text().strip(), os.environ)
    token = os.environ.get('GH_TOKEN')
    if not token:
        raise ValueError('The publication job requires its built-in GH_TOKEN')
    signature = bundle / 'SHA256SUMS.sigstore.json'
    if signature.is_symlink() or not signature.is_file():
        raise ValueError('Missing regular keyless signature bundle')
    # Revalidate the artifact transfer in this job, and pin the signing workflow identity.
    image = subprocess.check_output(['python3', str(source / 'scripts/verify-bundle.py'), str(bundle)], text=True).strip()
    subprocess.run(['cosign', 'verify-blob', str(bundle / 'SHA256SUMS'), '--bundle', str(signature),
                    '--certificate-identity', plan['identity'], '--certificate-oidc-issuer',
                    'https://token.actions.githubusercontent.com'], check=True)
    info = subprocess.check_output(['qemu-img', 'info', '--output=json', image], text=True)
    subprocess.run(['python3', str(source / 'scripts/check-image.py')], input=info, text=True, check=True)
    subprocess.run(['qemu-img', 'check', '-f', 'qcow2', image], check=True)
    require_absent(plan, token)
    # Creating the ref explicitly fails atomically if another publisher created it first.
    api('git/refs', token, payload={'ref': 'refs/tags/' + plan['tag'], 'sha': plan['commit']})
    with tempfile.TemporaryDirectory(prefix='vps-ci-release-') as directory:
        work = Path(directory)
        notes = work / 'notes.md'
        notes.write_text(f'''# VPS Linux {plan['tag']}

{'Development prerelease; not a stable production release.' if plan['prerelease'] else 'Stable versioned image.'}

Debian 13 amd64 server image, UEFI/GRUB, 8 GiB QCOW2, NoCloud key provisioning,
Docker/Compose V2, QEMU Guest Agent, security-only unattended upgrades and bounded logs.

The workflow passed static/integrity regressions, two independent guest boots,
Guest Agent RPC, 8-to-10 GiB root/GPT growth, effective security/log policy,
NTP synchronization, Docker Hub/HTTP, reboot and persistent identity checks.
Checksums, SPDX SBOM and a keyless Sigstore signature accompany the image.

Source: `{plan['commit']}`
Image SHA256: `{metadata['image_sha256']}`
Build and test run: {plan['run_url']}

Requires x86_64 QEMU/KVM-compatible UEFI without Secure Boot and NoCloud data.
Byte-for-byte reproducibility and universal cloud-provider compatibility are not claimed.
The build-time `boot_smoke_test: not_run` predates the subsequent acceptance run.
''')
        report = work / 'acceptance.json'
        report.write_text(json.dumps({'version': plan['version'], 'tag': plan['tag'],
            'source_commit': plan['commit'], 'source_dirty': False, 'image_sha256': metadata['image_sha256'],
            'workflow_run': plan['run_url'], 'result': 'passed', 'online_and_reboot': 'passed',
            'keyless_signature': 'verified',
            'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2) + '\n')
        names = ['vps-linux-v' + plan['version'] + '.qcow2', 'vps-linux-v' + plan['version'] + '.qcow2.sha256',
                 'SHA256SUMS', 'build.json', 'packages.tsv', 'sbom.spdx.json', 'SHA256SUMS.sigstore.json']
        command = ['gh', 'release', 'create', plan['tag'], '--repo', REPOSITORY, '--verify-tag', '--draft',
                   '--title', 'VPS Linux ' + plan['tag'], '--notes-file', str(notes)]
        if plan['prerelease']:
            command.append('--prerelease')
        subprocess.run(command + [str(bundle / name) for name in names] + [str(report)], check=True)
        downloaded = work / 'download'
        downloaded.mkdir()
        subprocess.run(['gh', 'release', 'download', plan['tag'], '--repo', REPOSITORY, '--dir', str(downloaded),
                        '--pattern', names[0], '--pattern', names[1]], check=True)
        # Compare the uploaded checksum with the independently validated artifact copy.
        if (downloaded / names[1]).read_bytes() != (bundle / names[1]).read_bytes():
            raise ValueError('Uploaded checksum differs from the tested artifact')
        subprocess.run(['sha256sum', '-c', names[1]], cwd=downloaded, check=True)
        subprocess.run(['gh', 'release', 'edit', plan['tag'], '--repo', REPOSITORY, '--draft=false',
                        '--latest=' + str(plan['latest']).lower()], check=True)
    url = f'https://github.com/{REPOSITORY}/releases/tag/{plan["tag"]}'
    print('Published: ' + url)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(f'## Published {plan["tag"]}\n\n{url}\n\nSource: `{plan["commit"]}`\n')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))

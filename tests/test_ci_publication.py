"""Policy/permission regression tests; never create actual GitHub tags or releases."""
import importlib.util
from pathlib import Path
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ci_publication', ROOT / 'scripts/publish-ci-release.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Publication(unittest.TestCase):
    def setUp(self):
        self.context = {'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REF': 'refs/heads/main',
                        'GITHUB_REPOSITORY': 'rxzsu/vps-linux', 'GITHUB_SHA': 'a' * 40,
                        'GITHUB_RUN_ID': '123456', 'GITHUB_RUN_ATTEMPT': '1'}
        self.metadata = {'version': '0.3-dev', 'source_commit': 'a' * 40, 'source_dirty': False}

    def plan(self, **changes):
        return module.publication_plan(self.metadata, self.metadata['version'], {**self.context, **changes})

    def test_development_is_unique_prerelease_not_latest(self):
        plan = self.plan()
        self.assertEqual(plan['tag'], 'v0.3-dev.123456.1')
        self.assertIs(plan['prerelease'], True)
        self.assertIs(plan['latest'], False)
        self.assertNotEqual(plan['tag'], self.plan(GITHUB_RUN_ATTEMPT='2')['tag'])
        self.assertEqual(plan['commit'], self.context['GITHUB_SHA'])

    def test_stable_uses_exact_version_tag(self):
        self.metadata['version'] = '0.3'
        plan = self.plan()
        self.assertEqual(plan['tag'], 'v0.3')
        self.assertIs(plan['prerelease'], False)
        self.assertIs(plan['latest'], True)

    def test_nonmanual_nonmain_and_foreign_repository_rejected(self):
        for changes in ({'GITHUB_EVENT_NAME': 'push'}, {'GITHUB_EVENT_NAME': 'pull_request'},
                        {'GITHUB_REF': 'refs/heads/feature/v0.3-operations'},
                        {'GITHUB_REPOSITORY': 'fork/vps-linux'}, {'GITHUB_SHA': 'bad'},
                        {'GITHUB_RUN_ID': '123;bad'}, {'GITHUB_RUN_ATTEMPT': '0'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.plan(**changes)

    def test_dirty_mismatched_and_unsafe_metadata_rejected(self):
        for changes in ({'source_dirty': True}, {'source_dirty': 'false'}, {'source_commit': 'b' * 40},
                        {'version': '../../v0.3'}):
            metadata = {**self.metadata, **changes}
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                module.publication_plan(metadata, '0.3-dev', self.context)

    def test_existing_tag_or_release_stops_publication(self):
        for existing in ('git/ref/tags/', 'releases/tags/'):
            def query(path, token, **kwargs):
                return {} if path.startswith(existing) else None
            with self.subTest(existing=existing), self.assertRaisesRegex(ValueError, 'already exists'):
                module.require_absent(self.plan(), 'test-token', query=query)

    def test_lookup_api_errors_fail_closed(self):
        def query(*args, **kwargs):
            raise RuntimeError('HTTP 403')
        with self.assertRaises(RuntimeError):
            module.require_absent(self.plan(), 'test-token', query=query)

    def test_only_read_404_is_missing_not_authorization_failure(self):
        endpoint = 'https://api.github.com/test'
        for code in (401, 403, 429, 500):
            with self.subTest(code=code), patch.object(module, 'urlopen', side_effect=HTTPError(endpoint, code, 'error', {}, None)):
                with self.assertRaises(RuntimeError):
                    module.api('test', 'test-token', missing_ok=True)
        with patch.object(module, 'urlopen', side_effect=HTTPError(endpoint, 404, 'not found', {}, None)):
            self.assertIsNone(module.api('test', 'test-token', missing_ok=True))
            with self.assertRaises(RuntimeError):
                module.api('git/refs', 'test-token', payload={'ref': 'refs/tags/test'}, missing_ok=True)


class WorkflowPublication(unittest.TestCase):
    def test_opt_in_gate_and_write_permission_are_isolated(self):
        workflow = yaml.load((ROOT / '.github/workflows/validate-build-system.yml').read_text(), Loader=yaml.BaseLoader)
        inputs = workflow['on']['workflow_dispatch']['inputs']
        self.assertEqual(inputs['publish_release']['default'], 'false')
        self.assertEqual(workflow['permissions']['contents'], 'read')
        self.assertEqual(workflow['jobs']['build-and-boot']['permissions']['contents'], 'read')
        publish = workflow['jobs']['publish']
        self.assertEqual(publish['needs'], 'build-and-boot')
        self.assertEqual(publish['permissions']['contents'], 'write')
        for required in ('workflow_dispatch', 'inputs.publish_release', 'inputs.build_and_boot', 'inputs.online_tests', 'refs/heads/main'):
            self.assertIn(required, publish['if'])
        self.assertEqual(publish['concurrency']['cancel-in-progress'], 'false')
        download = next(step for step in publish['steps'] if step.get('uses', '').startswith('actions/download-artifact@'))
        self.assertIn('needs.build-and-boot.outputs.image_artifact_id', download['with']['artifact-ids'])
        self.assertEqual(download['with']['digest-mismatch'], 'error')

    def test_publication_forces_transfer_even_when_download_checkbox_off(self):
        workflow = yaml.load((ROOT / '.github/workflows/validate-build-system.yml').read_text(), Loader=yaml.BaseLoader)
        steps = workflow['jobs']['build-and-boot']['steps']
        staging = next(step for step in steps if step.get('name') == 'Stage successfully tested image bundle')
        upload = next(step for step in steps if step.get('id') == 'upload_image')
        for step in (staging, upload):
            self.assertIn('inputs.upload_image || inputs.publish_release', step['if'])

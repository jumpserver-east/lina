#!/usr/bin/env python3
"""Run the workflow's actual policy shell against a disposable GitHub CLI stub."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / 'workflows/sync-version-branches.yml'


class WorkflowPolicyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        workflow = WORKFLOW.read_text()
        step = workflow.split('      - name: Keep only jumpserver-east workflows enabled\n', 1)[1]
        self.script = textwrap.dedent(step.split('        run: |\n', 1)[1].split('\n  sync:', 1)[0])
        build = ('dispatch-web-image.yml' if 'dispatch-web-image.yml' in self.script
                 else 'build-component-image.yml')
        self.workflows = [
            [1, '.github/workflows/sync-version-branches.yml', 'active'],
            [2, '.github/workflows/' + build, 'active'],
            [3, 'dynamic/dependabot/update-graph', 'active'],
            [4, '.github/workflows/jms-build-test.yml', 'active'],
            [5, '.github/workflows/removed.yml', 'deleted'],
            [6, '.github/workflows/already-disabled.yml', 'disabled_manually'],
            [7, '.github/workflows/legacy.yaml', 'active'],
        ]
        cli = self.root / 'gh'
        cli.write_text('#!' + sys.executable + '\n' + textwrap.dedent('''\
            import json
            import os
            from pathlib import Path
            import sys

            root = Path(os.environ['RUNNER_TEMP'])
            args = sys.argv[1:]
            with (root / 'calls.jsonl').open('a') as stream:
                stream.write(json.dumps(args) + '\\n')
            if '--paginate' in args:
                for workflow in json.loads((root / 'fixtures.json').read_text()):
                    print('\\t'.join(str(value) for value in workflow))
                sys.exit(0)
            endpoint = next(arg for arg in args if arg.startswith('repos/'))
            workflow_id = endpoint.split('/')[5]
            if '--method' in args:
                if workflow_id == os.environ.get('FAIL_DISABLE') or workflow_id == '3':
                    print('gh: Unable to disable this workflow. (HTTP 422)', file=sys.stderr)
                    sys.exit(1)
                (root / ('disabled-' + workflow_id)).touch()
            else:
                if workflow_id == os.environ.get('FAIL_VERIFY'):
                    sys.exit(1)
                if workflow_id == os.environ.get('STILL_ACTIVE'):
                    print('active')
                else:
                    print('disabled_manually')
            '''))
        cli.chmod(0o755)

    def run_policy(self, **settings):
        (self.root / 'fixtures.json').write_text(json.dumps(self.workflows))
        summary = self.root / 'summary.md'
        result = subprocess.run(
            ['bash', '-c', self.script], capture_output=True, text=True, timeout=10,
            env={**os.environ, **settings, 'PATH': str(self.root) + os.pathsep + os.environ['PATH'],
                 'RUNNER_TEMP': str(self.root), 'GITHUB_STEP_SUMMARY': str(summary),
                 'GH_REPO': 'jumpserver-east/koko'},
        )
        calls = [json.loads(line) for line in (self.root / 'calls.jsonl').read_text().splitlines()]
        disabled = [call[call.index('--method') + 2] for call in calls if '--method' in call]
        return result, summary.read_text(), disabled

    def test_managed_and_owned_workflows_are_not_sent_to_disable_api(self):
        result, summary, disabled = self.run_policy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(disabled, [
            'repos/jumpserver-east/koko/actions/workflows/4/disable',
            'repos/jumpserver-east/koko/actions/workflows/7/disable',
        ])
        self.assertIn('dynamic/dependabot/update-graph | managed by GitHub; skipped', summary)
        self.assertIn('Disabling inherited workflow: .github/workflows/jms-build-test.yml', result.stdout)
        self.assertIn('legacy.yaml | disabled_manually', summary)

    def test_real_yaml_disable_error_is_not_ignored(self):
        result, summary, disabled = self.run_policy(FAIL_DISABLE='4')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HTTP 422', result.stderr)
        self.assertIn('::error::Failed to disable inherited workflow: .github/workflows/jms-build-test.yml', result.stdout)
        self.assertIn('jms-build-test.yml | FAILED to disable', summary)
        self.assertTrue(disabled[-1].endswith('/7/disable'))

    def test_verification_request_failure_is_reported(self):
        result, summary, _ = self.run_policy(FAIL_VERIFY='4')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('jms-build-test.yml | FAILED to verify', summary)
        self.assertIn('legacy.yaml | disabled_manually', summary)

    def test_workflow_still_active_after_disable_fails(self):
        result, summary, _ = self.run_policy(STILL_ACTIVE='4')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('jms-build-test.yml | active', summary)


if __name__ == '__main__':
    unittest.main(verbosity=2)

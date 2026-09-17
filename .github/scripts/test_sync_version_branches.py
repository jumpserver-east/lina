#!/usr/bin/env python3
"""Exercise actual Git fetch/push behavior using disposable local repositories."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shlex
import subprocess
import tempfile
from threading import Thread
import unittest


SCRIPT = Path(__file__).with_name('sync-version-branches.sh').resolve()


class SyncVersionBranchesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1',
                        GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME='Sync Test', GIT_AUTHOR_EMAIL='test@example.com',
                        GIT_COMMITTER_NAME='Sync Test', GIT_COMMITTER_EMAIL='test@example.com')
        self.seed = self.root / 'seed'
        self.upstream = self.root / 'upstream.git'
        self.origin = self.root / 'origin.git'
        self.work = self.root / 'work'
        for repo in (self.upstream, self.origin):
            self.git(self.root, 'init', '--bare', str(repo))
        self.git(self.root, 'init', str(self.seed))
        self.git(self.seed, 'checkout', '-b', 'docker-build')
        self.base = self.commit('base')
        self.git(self.seed, 'push', str(self.origin), 'HEAD:refs/heads/docker-build')
        self.git(self.origin, 'symbolic-ref', 'HEAD', 'refs/heads/docker-build')
        self.git(self.root, 'clone', str(self.origin), str(self.work))
        self.git(self.work, 'config', 'push.followTags', 'true')

    def git(self, cwd, *args):
        return subprocess.run(['git', *args], cwd=cwd, env=self.env, check=True,
                              text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).stdout.strip()

    def commit(self, message, parent=None):
        if parent:
            self.git(self.seed, 'checkout', '--detach', parent)
        self.git(self.seed, 'commit', '--allow-empty', '-m', message)
        return self.git(self.seed, 'rev-parse', 'HEAD')

    def branch(self, repo, name, sha):
        self.git(self.seed, 'push', str(repo), f'{sha}:refs/heads/{name}')

    def refs(self, repo):
        output = self.git(repo, 'for-each-ref', '--format=%(refname) %(objectname)')
        return dict(line.split() for line in output.splitlines())

    def sync(self, dry_run='true'):
        summary = self.root / 'summary.md'
        summary.write_text('')
        env = dict(self.env, UPSTREAM_URL=str(self.upstream), DRY_RUN=dry_run,
                   GITHUB_STEP_SUMMARY=str(summary))
        result = subprocess.run(['bash', str(SCRIPT)], cwd=self.work, env=env,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result, summary.read_text()

    def test_only_release_branches_are_created_and_source_is_unchanged(self):
        accepted = ['v4.10.14-lts', 'v3.10.23-lts', 'v3.10.0-7-lts', 'v5.0.0']
        ignored = ['main', 'master', 'docker-build', 'v6', 'dev-test', 'dev/feature',
                   'v3-test', 'v4-test', 'v5-test',
                   'v4.10', 'v3.10.21-lts-hthx', 'v4.10.14-lts.patch',
                   'pr@v4.10.14-lts', 'feature/v4.10.14-lts', 'v4.10.14-rc1']
        for branch in accepted + ignored:
            self.branch(self.upstream, branch, self.base)
        self.git(self.seed, 'tag', '-a', 'v9.0.0-lts', '-m', 'tag only')
        self.git(self.seed, 'push', str(self.upstream), 'refs/tags/v9.0.0-lts')
        # Even a local annotated tag and push.followTags=true must not leak tags.
        self.git(self.work, 'tag', '-a', 'local-tag', '-m', 'local tag')
        before_source = self.refs(self.upstream)
        result, _ = self.sync('false')
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = {f'refs/heads/{b}': self.base for b in accepted + ['docker-build']}
        self.assertEqual(self.refs(self.origin), expected)
        self.assertEqual(self.refs(self.upstream), before_source)
        result, summary = self.sync('false')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Create: 0; update: 0; mirror: 0; unchanged: 4;', summary)

    def test_fast_forward_divergence_ahead_and_origin_only_branches(self):
        newer = self.commit('upstream change')
        fork_change = self.commit('fork change', self.base)
        for branch, source, dest in [
            ('v4.10.14-lts', newer, self.base),
            ('v3.10.23-lts', newer, fork_change),
            ('v4.10.15-lts', self.base, newer),
            ('v4.10.16-lts', newer, newer),
        ]:
            self.branch(self.upstream, branch, source)
            self.branch(self.origin, branch, dest)
        self.branch(self.origin, 'v1.2.3-lts', self.base)
        source_before, origin_before = self.refs(self.upstream), self.refs(self.origin)
        result, summary = self.sync('false')
        self.assertEqual(result.returncode, 0, result.stderr)
        origin_before['refs/heads/v4.10.14-lts'] = newer
        self.assertEqual(self.refs(self.origin), origin_before)
        self.assertEqual(self.refs(self.upstream), source_before)
        self.assertIn('update: 1; mirror: 0; unchanged: 1; skipped: 2;', summary)

    def test_development_branches_mirror_upstream_and_discard_origin_commits(self):
        newer = self.commit('upstream change')
        fork_change = self.commit('fork change', self.base)
        for branch, source, dest in [
            ('dev', newer, fork_change),  # Diverged histories.
            ('v3', self.base, fork_change),  # Roll back origin-only commits.
            ('v4', newer, self.base),  # Fast-forward origin.
            ('v5', newer, None),  # Create a missing branch.
        ]:
            self.branch(self.upstream, branch, source)
            if dest:
                self.branch(self.origin, branch, dest)
        # Similar names and the workflow branch must not be mirrored.
        for branch in ('docker-build', 'main', 'v6', 'dev-test'):
            self.branch(self.upstream, branch, newer)
            self.branch(self.origin, branch, self.base)
        source_before = self.refs(self.upstream)
        expected = self.refs(self.origin)
        expected.update({f'refs/heads/{b}': sha for b, sha in
                         [('dev', newer), ('v3', self.base), ('v4', newer), ('v5', newer)]})
        result, summary = self.sync('false')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.refs(self.origin), expected)
        self.assertEqual(self.refs(self.upstream), source_before)
        self.assertIn('Create: 1; update: 0; mirror: 3;', summary)
        result, summary = self.sync('false')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Create: 0; update: 0; mirror: 0; unchanged: 4;', summary)

    def test_development_mirror_lease_rejects_concurrent_updates_and_creation(self):
        newer = self.commit('upstream change')
        concurrent = self.commit('concurrent origin change', self.base)
        self.branch(self.origin, 'dev', self.base)
        self.branch(self.origin, 'concurrent-change', concurrent)
        for branch in ('dev', 'v5'):
            self.branch(self.upstream, branch, newer)
        # Change the remote after its snapshot is read, before push advertises refs.
        # This exercises real --force-with-lease rejection for existing and new heads.
        hook = self.work / '.git' / 'hooks' / 'reference-transaction'
        hook.write_text(
            '#!/bin/sh\n'
            '[ "$1" = committed ] || exit 0\n'
            'while read -r old new ref; do\n'
            '  case "$ref" in\n'
            '    refs/remotes/version-sync/dev|refs/remotes/version-sync/v5)\n'
            '      branch="${ref#refs/remotes/version-sync/}"\n'
            f'      git --git-dir={shlex.quote(str(self.origin))} '
            f'update-ref "refs/heads/$branch" {concurrent}\n'
            '      ;;\n'
            '  esac\n'
            'done\n'
        )
        hook.chmod(0o755)
        source_before = self.refs(self.upstream)
        result, summary = self.sync('false')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('failed: 2;', summary)
        for branch in ('dev', 'v5'):
            self.assertEqual(self.refs(self.origin)[f'refs/heads/{branch}'], concurrent)
        self.assertEqual(self.refs(self.upstream), source_before)

    def test_dry_run_previews_creation_and_update_without_writing_remotes(self):
        newer = self.commit('upstream change')
        self.branch(self.upstream, 'v4.10.14-lts', newer)
        self.branch(self.upstream, 'v3.10.23-lts', newer)
        self.branch(self.origin, 'v4.10.14-lts', self.base)
        fork_change = self.commit('fork change', self.base)
        self.branch(self.upstream, 'dev', newer)
        self.branch(self.origin, 'dev', fork_change)
        self.branch(self.upstream, 'v3', self.base)
        self.branch(self.origin, 'v3', fork_change)
        self.branch(self.upstream, 'v5', newer)
        before_source, before_dest = self.refs(self.upstream), self.refs(self.origin)
        result, summary = self.sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Would Create', summary)
        self.assertIn('Would Update', summary)
        self.assertIn('Would Mirror upstream (discard origin-only commits)', summary)
        self.assertIn('mirror: 2;', summary)
        self.assertEqual(self.refs(self.upstream), before_source)
        self.assertEqual(self.refs(self.origin), before_dest)

    def test_empty_or_unmatched_source_preserves_origin_only_branches(self):
        self.branch(self.origin, 'dev', self.base)
        self.branch(self.origin, 'v5', self.base)
        before = self.refs(self.origin)
        for with_main in (False, True):
            if with_main:
                self.branch(self.upstream, 'main', self.base)
            result, summary = self.sync('false')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Create: 0; update: 0;', summary)
            self.assertEqual(self.refs(self.origin), before)

    def test_push_rejection_is_reported_and_other_branches_continue(self):
        self.branch(self.upstream, 'v3.10.23-lts', self.base)
        self.branch(self.upstream, 'v4.10.14-lts', self.base)
        hook = self.origin / 'hooks' / 'update'
        hook.write_text('#!/bin/sh\n[ "$1" != refs/heads/v3.10.23-lts ]\n')
        hook.chmod(0o755)
        result, summary = self.sync('false')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAILED to Create', summary)
        self.assertIn('failed: 1;', summary)
        self.assertNotIn('refs/heads/v3.10.23-lts', self.refs(self.origin))
        self.assertIn('refs/heads/v4.10.14-lts', self.refs(self.origin))

    def test_http_push_permission_denial_stops_remaining_branches(self):
        self.branch(self.upstream, 'v3.10.23-lts', self.base)
        self.branch(self.upstream, 'v4.10.14-lts', self.base)
        self.env['SYNC_TOKEN_SOURCE'] = 'SYNC_BRANCHES_TOKEN'
        before_source, before_dest = self.refs(self.upstream), self.refs(self.origin)
        requests = []

        class DeniedPushHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                body = b'Permission to jumpserver-east/jumpserver.git denied to Nickyang00.\n'
                self.send_response(403)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        # Keep reads on the real local repository, but have Git's HTTP transport
        # encounter the same repository-wide denial as a GitHub push.
        with ThreadingHTTPServer(('127.0.0.1', 0), DeniedPushHandler) as server:
            self.git(self.work, 'config', 'remote.origin.pushurl',
                     f'http://127.0.0.1:{server.server_port}/origin.git')
            self.git(self.work, 'config', 'http.proxy', '')
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result, _ = self.sync()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(requests, [])
                result, summary = self.sync('false')
            finally:
                server.shutdown()
                thread.join()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('The requested URL returned error: 403', result.stderr)
        self.assertEqual(requests, ['/origin.git/info/refs?service=git-receive-pack'])
        self.assertIn('Push credential: SYNC_BRANCHES_TOKEN', summary)
        self.assertIn('origin denied authentication or repository write access', summary)
        self.assertIn('Sync stopped: remaining branches were not attempted', summary)
        self.assertIn('Contents and Workflows write permissions', summary)
        self.assertIn('failed: 1;', summary)
        self.assertNotIn('| v4.10.14-lts |', summary)
        self.assertEqual(self.refs(self.upstream), before_source)
        self.assertEqual(self.refs(self.origin), before_dest)

    def test_invalid_dry_run_is_rejected(self):
        before = self.refs(self.origin)
        result, _ = self.sync('yes')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DRY_RUN must be true or false', result.stderr)
        self.assertEqual(self.refs(self.origin), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)

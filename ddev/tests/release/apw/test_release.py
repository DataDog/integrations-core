# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ddev.release.apw import FILES, Release, api_get

COMMIT = 'a' * 40
REPOSITORY = 'DataDog/integrations-core'


class TestRelease:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.directory = tmp_path
        self.release = Release(REPOSITORY, COMMIT)
        archive = b'source snapshot'
        checksum = hashlib.sha256(archive).hexdigest()
        self.content = {
            FILES[0]: archive,
            'release.json': json.dumps(
                {
                    'format_version': 1,
                    'repository': REPOSITORY,
                    'commit': COMMIT,
                    'archive': FILES[0],
                    'sha256': checksum,
                }
            ).encode(),
            'SHA256SUMS': f'{checksum}  {FILES[0]}\n'.encode(),
        }
        for name, content in self.content.items():
            (self.directory / name).write_bytes(content)
        self.remote = None
        self.ref = None
        self.mutations = []
        self.downloads = []
        self.fail_upload = None
        monkeypatch.setattr('ddev.release.apw.api_get', self.api)
        monkeypatch.setattr('ddev.release.apw.gh', self.gh)
        monkeypatch.setenv('GITHUB_SERVER_URL', 'https://github.com')
        monkeypatch.setenv('GITHUB_RUN_ID', '123')
        monkeypatch.setenv('GH_REPO', 'wrong/implicit-repository')

    def asset(self, name: str) -> dict[str, Any]:
        content = self.content[name]
        return {
            'id': FILES.index(name) + 1,
            'name': name,
            'state': 'uploaded',
            'size': len(content),
            'digest': 'sha256:' + hashlib.sha256(content).hexdigest(),
        }

    def seed(self, *, draft: bool = False, files: tuple[str, ...] = FILES) -> None:
        self.remote = {
            'id': 42,
            'tag_name': self.release.tag,
            'target_commitish': COMMIT,
            'prerelease': True,
            'draft': draft,
            'assets': [self.asset(name) for name in files],
        }

    def api(self, endpoint: str, missing_ok: bool = False) -> dict[str, Any] | None:
        if '/git/ref/' in endpoint:
            return self.ref
        if '/tags/' in endpoint and (self.remote is None or self.remote['draft']):
            return None
        return copy.deepcopy(self.remote)

    def gh(self, *args: str) -> bytes:
        if args[0] == 'api':
            if '--method' in args:
                assert args[args.index('--method') + 1] == 'POST'
                assert args[3] == f'repos/{REPOSITORY}/git/refs'
                fields = dict(args[index + 1].split('=', 1) for index, arg in enumerate(args) if arg == '-f')
                assert fields['ref'] == f'refs/tags/{self.release.tag}'
                assert self.ref is None
                self.ref = {'object': {'type': 'commit', 'sha': fields['sha']}}
                self.mutations.append(args)
                return json.dumps(self.ref).encode()
            if '--paginate' in args:
                return json.dumps([[], [self.remote] if self.remote else []]).encode()
            name = FILES[int(args[1].rsplit('/', 1)[1]) - 1]
            self.downloads.append(name)
            return self.content[name]
        assert args[args.index('--repo') + 1] == REPOSITORY
        command = args[1]
        if command == 'view':
            return b'{"databaseId": 42}'
        self.mutations.append(args)
        if command == 'create':
            assert '--draft' in args
            assert '--prerelease' in args
            assert '--latest=false' in args
            assert args[args.index('--target') + 1] == COMMIT
            self.seed(draft=True, files=())
        elif command == 'upload':
            name = Path(args[3]).name
            assert self.remote['draft']
            assert '--clobber' not in args
            assert name not in [a['name'] for a in self.remote['assets']]
            if self.fail_upload == name:
                raise subprocess.CalledProcessError(1, args)
            self.remote['assets'].append(self.asset(name))
        elif command == 'edit':
            assert {a['name'] for a in self.remote['assets']} == set(FILES)
            assert '--draft=false' in args
            assert '--latest=false' in args
            self.remote['draft'] = False
        else:
            pytest.fail(f'unexpected mutation: {args}')
        return b''

    @pytest.mark.parametrize(
        'ref',
        [
            None,
            {'object': {'type': 'commit', 'sha': COMMIT}},
            {'object': {'type': 'commit', 'sha': 'b' * 40}},
            {'object': {'type': 'tag', 'sha': COMMIT}},
        ],
    )
    def test_ensure_tag_only_creates_missing_refs(self, ref: dict[str, Any] | None):
        self.ref = copy.deepcopy(ref)
        expected = {'object': {'type': 'commit', 'sha': COMMIT}}
        if ref is not None and ref != expected:
            with pytest.raises(ValueError, match='existing tag does not point'):
                self.release.ensure_tag()
            assert self.ref == ref
            assert self.mutations == []
        else:
            self.release.ensure_tag()
            assert self.ref == expected
            assert len(self.mutations) == (1 if ref is None else 0)
        assert self.remote is None  # The tag token never creates or uploads a release.

    def test_unchanged_release_skips_without_downloading_archive_or_writing(self):
        self.seed()
        assert not self.release.needs_package()
        assert self.downloads == ['release.json', 'SHA256SUMS']
        assert self.mutations == []

    def test_missing_release_is_packaged_and_published_as_prerelease(self):
        assert self.release.needs_package()
        self.release.publish(self.directory)
        assert not self.remote['draft']
        assert [call[1] for call in self.mutations] == ['create', 'upload', 'upload', 'upload', 'edit']

    def test_interrupted_upload_resumes_without_replacing_uploaded_assets(self):
        self.fail_upload = 'release.json'
        with pytest.raises(subprocess.CalledProcessError):
            self.release.publish(self.directory)
        assert self.remote['draft']
        assert [a['name'] for a in self.remote['assets']] == [FILES[0]]
        self.mutations.clear()
        self.fail_upload = None
        assert self.release.needs_package()
        self.release.publish(self.directory)
        assert [call[1] for call in self.mutations] == ['upload', 'upload', 'edit']
        assert FILES[0] not in [Path(call[3]).name for call in self.mutations if call[1] == 'upload']

    def test_fully_uploaded_draft_only_needs_publication(self):
        self.seed(draft=True)
        self.release.publish(self.directory)
        assert [call[1] for call in self.mutations] == ['edit']

    def test_publish_rerun_does_not_mutate_published_release(self):
        self.seed()
        self.release.publish(self.directory)
        assert self.mutations == []

    def test_incomplete_published_release_fails_instead_of_skipping_or_repairing(self):
        self.seed(files=(FILES[0],))
        with pytest.raises(ValueError):
            self.release.needs_package()
        with pytest.raises(ValueError):
            self.release.publish(self.directory)
        assert self.mutations == []

    @pytest.mark.parametrize('draft', [False, True])
    def test_mismatched_uploads_are_never_replaced(self, draft: bool):
        self.seed(draft=draft)
        self.remote['assets'][0]['digest'] = 'sha256:' + '0' * 64
        with pytest.raises(ValueError):
            self.release.publish(self.directory)
        assert self.mutations == []

    @pytest.mark.parametrize(
        'mutate',
        [
            lambda r: r.update(target_commitish='b' * 40),
            lambda r: r.update(prerelease=False),
            lambda r: r['assets'][0].update(state='starter'),
            lambda r: r['assets'][0].update(size=0),
            lambda r: r['assets'][0].update(digest=None),
            lambda r: r['assets'].append(dict(r['assets'][0])),
            lambda r: r['assets'].append({'name': 'unexpected'}),
        ],
    )
    def test_invalid_release_state_fails_closed(self, mutate: Callable[[dict[str, Any]], None]):
        self.seed()
        mutate(self.remote)
        with pytest.raises(ValueError):
            self.release.needs_package()
        with pytest.raises(ValueError):
            self.release.publish(self.directory)
        assert self.mutations == []

    def test_wrong_metadata_identity_is_not_an_unchanged_success(self):
        metadata = json.loads(self.content['release.json'])
        metadata['commit'] = 'b' * 40
        self.content['release.json'] = json.dumps(metadata).encode()
        self.seed()
        with pytest.raises(ValueError):
            self.release.needs_package()
        assert self.mutations == []

    def test_corrupt_local_archive_fails_before_writing(self):
        (self.directory / FILES[0]).write_bytes(b'corrupt snapshot')
        with pytest.raises(ValueError):
            self.release.publish(self.directory)
        assert self.mutations == []

    def test_existing_tag_pointing_elsewhere_is_rejected(self):
        self.ref = {'object': {'type': 'commit', 'sha': 'b' * 40}}
        with pytest.raises(ValueError):
            self.release.publish(self.directory)
        assert self.mutations == []

    @pytest.mark.parametrize('commit', ['main', 'HEAD', 'abc123', '--bad'])
    def test_invalid_commit_is_rejected(self, commit: str):
        with pytest.raises(ValueError, match='full, lowercase Git SHA'):
            Release(REPOSITORY, commit)

    @pytest.mark.parametrize('repository', ['repository', '../repository', 'owner/repo/path', '--repo=wrong', ''])
    def test_invalid_repository_is_rejected(self, repository: str):
        with pytest.raises(ValueError, match='owner/repository'):
            Release(repository, COMMIT)


class TestAPIError:
    @pytest.mark.parametrize('status, code', [(200, 0), (404, 1), (401, 1), (403, 1), (429, 1), (500, 1)])
    def test_only_explicit_404_means_missing(self, status: int, code: int):
        response = subprocess.CompletedProcess(
            ['gh', 'api'],
            code,
            stdout=f'HTTP/2.0 {status} Status\nHeader: value\n\n{{"id":42}}',
            stderr='error' if code else '',
        )
        with patch('ddev.release.apw.subprocess.run', return_value=response):
            if status == 404:
                assert api_get('endpoint', missing_ok=True) is None
            elif status == 200:
                assert api_get('endpoint', missing_ok=True) == {'id': 42}
            else:
                with pytest.raises(subprocess.CalledProcessError):
                    api_get('endpoint', missing_ok=True)

    def test_connection_error_is_not_missing(self):
        response = subprocess.CompletedProcess(['gh', 'api'], 1, stdout='', stderr='connection failed')
        with patch('ddev.release.apw.subprocess.run', return_value=response):
            with pytest.raises(subprocess.CalledProcessError):
                api_get('endpoint', missing_ok=True)

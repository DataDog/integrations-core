# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import gzip
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from ddev.release.apw import package


class TestPackage:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.root = tmp_path
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '--quiet')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'commit.gpgSign', 'false')
        self.git('config', 'core.hooksPath', '/dev/null')

    def git(self, *args: str) -> str:
        return subprocess.check_output(['git', '-C', str(self.repo), *args]).decode().strip()

    def commit(self, files: dict[str, bytes]) -> str:
        for name, content in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.git('add', '.')
        self.git('commit', '--quiet', '-m', 'Fixture')
        return self.git('rev-parse', 'HEAD')

    def test_snapshot_is_repeatable_and_ignores_working_tree(self):
        commit = self.commit(
            {'example/assets/dashboard.json': b'{"title":"Committed dashboard"}', 'example/manifest.json': b'{}'}
        )
        first = package(self.repo, 'DataDog/integrations-core', commit, self.root / 'first')
        (self.repo / 'example/assets/dashboard.json').write_text('uncommitted modification')
        (self.repo / 'example/assets/untracked.json').write_text('do not publish')
        second = package(self.repo, 'DataDog/integrations-core', commit, self.root / 'second')
        first_bytes = (self.root / 'first/apw-assets.tar.gz').read_bytes()
        assert first_bytes == (self.root / 'second/apw-assets.tar.gz').read_bytes()
        assert first == second
        assert first['commit'] == commit
        assert first['repository'] == 'DataDog/integrations-core'
        assert first['sha256'] == hashlib.sha256(first_bytes).hexdigest()
        assert json.loads((self.root / 'first/release.json').read_text()) == first
        assert (self.root / 'first/SHA256SUMS').read_text() == f"{first['sha256']}  apw-assets.tar.gz\n"
        with tarfile.open(fileobj=io.BytesIO(first_bytes), mode='r:gz') as archive:
            assert {member.name for member in archive if member.isfile()} == {
                'repo/example/assets/dashboard.json',
                'repo/example/manifest.json',
            }
            assert (
                archive.extractfile('repo/example/assets/dashboard.json').read() == b'{"title":"Committed dashboard"}'
            )
        with pytest.raises(FileExistsError):
            package(self.repo, 'DataDog/integrations-core', commit, self.root / 'first')

    def test_exports_complete_snapshot_including_new_asset_paths(self):
        self.commit(
            {
                'README.md': b'repository documentation',
                '.github/workflows/test.yml': b'workflow',
                'scripts/package.py': b'packaging code',
                'example/manifest.json': b'{}',
                'example/assets/dashboard.json': b'{}',
                'example/interfaces/example/config.md': b'interface',
                'example/future-format/definition.bin': bytes(range(256)),
                'example/future-format/.metadata': b'new format metadata',
                'example/tests/test_check.py': b'test code',
                'example/' + 'long-name-' * 15 + '.json': b'{}',
                'example/images/screenshot with spaces.png': b'image',
            }
        )
        (self.repo / 'scripts/package.py').chmod(0o755)
        (self.repo / 'example/link.json').symlink_to('manifest.json')
        self.git('add', '.')
        self.git('commit', '--quiet', '-m', 'Executable and symlink')
        commit = self.git('rev-parse', 'HEAD')
        package(self.repo, 'DataDog/integrations-core', commit, self.root / 'snapshot')
        original = subprocess.check_output(
            ['git', '-C', str(self.repo), 'archive', '--format=tar', '--prefix=repo/', commit]
        )
        with gzip.open(self.root / 'snapshot/apw-assets.tar.gz', 'rb') as archive:
            assert archive.read() == original

    def test_git_archive_failure_does_not_produce_a_release(self):
        self.commit({'README.md': b'repository documentation'})
        with pytest.raises(subprocess.CalledProcessError):
            package(self.repo, 'DataDog/integrations-core', '0' * 40, self.root / 'failed')
        assert not (self.root / 'failed/apw-assets.tar.gz').exists()
        assert not (self.root / 'failed/release.json').exists()

    def test_excludes_only_agent_vendor_directories(self):
        excluded = {
            'example/datadog_checks/example/vendor/check.jar': b'vendored jar',
            'another/datadog_checks/package/vendor/nested/dependency.bin': b'vendored binary',
        }
        retained = {
            'example/manifest.json': b'{}',
            'example/datadog_checks/example/check.py': b'Agent check',
            'example/datadog_checks/example/assets/exporter/handler.php': b'exporter asset',
            'example/assets/vendor/dependency.bin': b'asset payload',
            'example/interfaces/new/definition.json': b'new interface',
            'example/future-format/definition.bin': b'new asset format',
            'example/vendor/asset.bin': b'outside Agent package',
        }
        commit = self.commit({**excluded, **retained})
        package(self.repo, 'DataDog/marketplace', commit, self.root / 'snapshot', ('*/datadog_checks/*/vendor/**',))
        with tarfile.open(self.root / 'snapshot/apw-assets.tar.gz', 'r:gz') as archive:
            actual = {member.name: archive.extractfile(member).read() for member in archive if member.isfile()}
        assert actual == {'repo/' + path: content for path, content in retained.items()}

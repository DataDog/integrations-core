# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

AARCH64_HASH = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2'
X86_64_HASH = 'f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5'


def _make_sha256sums(version, release, archs=('aarch64', 'x86_64')):
    """Build realistic SHA256SUMS content with unrelated entries to verify correct filtering."""
    hashes = {'aarch64': AARCH64_HASH, 'x86_64': X86_64_HASH}
    lines = []
    for arch in archs:
        filename = f'cpython-{version}+{release}-{arch}-apple-darwin-install_only_stripped.tar.gz'
        lines.append(f'{hashes[arch]}  {filename}')
    lines.append(f'{"0" * 64}  cpython-{version}+{release}-aarch64-unknown-linux-gnu-install_only_stripped.tar.gz')
    return '\n'.join(lines)


def test_update_python_version_success(fake_repo, ddev, mocker):
    """Test successful Python version update."""
    # Mock the constants that get imported by the upgrade script
    mocker.patch('ddev.repo.constants.PYTHON_VERSION_FULL', '3.13.7')
    mocker.patch('ddev.repo.constants.PYTHON_VERSION', '3.13')

    # Mock network calls
    mocker.patch('ddev.cli.meta.scripts.upgrade_python.get_latest_python_version', return_value='3.13.9')
    mocker.patch(
        'ddev.cli.meta.scripts.upgrade_python.get_python_sha256_hashes',
        return_value={
            'linux_source_sha256': 'c4c066af19c98fb7835d473bebd7e23be84f6e9874d47db9e39a68ee5d0ce35c',
            'windows_amd64_sha256': '200ddff856bbff949d2cc1be42e8807c07538abd6b6966d5113a094cf628c5c5',
        },
    )
    mocker.patch(
        'ddev.cli.meta.scripts.upgrade_python.get_pbs_release_info',
        return_value={
            'release': '20251210',
            'aarch64': 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
            'x86_64': 'f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5',
        },
    )

    result = ddev('meta', 'scripts', 'upgrade-python-version')

    assert result.exit_code == 0, result.output
    assert 'Updating Python from 3.13.7 to 3.13.9' in result.output
    assert 'Passed: 5' in result.output
    assert 'Python version upgraded from 3.13.7 to 3.13.9' in result.output

    # Verify constants.py was updated
    constants_file = fake_repo.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'
    contents = constants_file.read_text()
    assert "PYTHON_VERSION_FULL = '3.13.9'" in contents
    assert "PYTHON_VERSION_FULL = '3.13.7'" not in contents

    # Verify Linux Dockerfile was updated
    linux_dockerfile = fake_repo.path / '.builders' / 'images' / 'linux-aarch64' / 'Dockerfile'
    contents = linux_dockerfile.read_text()
    assert 'ENV PYTHON3_VERSION=3.13.9' in contents
    assert 'SHA256="c4c066af19c98fb7835d473bebd7e23be84f6e9874d47db9e39a68ee5d0ce35c"' in contents
    assert 'ENV PYTHON3_VERSION=3.13.7' not in contents

    # Verify Windows Dockerfile was updated
    windows_dockerfile = fake_repo.path / '.builders' / 'images' / 'windows-x86_64' / 'Dockerfile'
    contents = windows_dockerfile.read_text()
    assert 'ENV PYTHON_VERSION="3.13.9"' in contents
    assert '-Hash \'200ddff856bbff949d2cc1be42e8807c07538abd6b6966d5113a094cf628c5c5\'' in contents
    assert 'ENV PYTHON_VERSION="3.13.7"' not in contents

    # Verify macOS workflow was updated with PBS format
    workflow_file = fake_repo.path / '.github' / 'workflows' / 'resolve-build-deps.yaml'
    contents = workflow_file.read_text()
    assert 'PYTHON_PATCH: 9' in contents
    assert 'PYTHON_PATCH: 7' not in contents
    assert 'PBS_RELEASE: 20251210' in contents
    assert 'PBS_SHA256__aarch64: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2' in contents
    assert 'PBS_SHA256__x86_64: f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5' in contents


def test_update_python_version_already_latest(fake_repo, ddev, mocker):
    # Mock the constants that get imported by the upgrade script
    mocker.patch('ddev.repo.constants.PYTHON_VERSION_FULL', '3.13.7')
    mocker.patch('ddev.repo.constants.PYTHON_VERSION', '3.13')

    mocker.patch('ddev.cli.meta.scripts.upgrade_python.get_latest_python_version', return_value='3.13.7')

    result = ddev('meta', 'scripts', 'upgrade-python-version')

    assert result.exit_code == 0, result.output
    assert 'Already at latest Python version: 3.13.7' in result.output


def test_update_python_version_no_new_version_found(fake_repo, ddev, mocker):
    mocker.patch('ddev.cli.meta.scripts.upgrade_python.get_latest_python_version', return_value=None)

    result = ddev('meta', 'scripts', 'upgrade-python-version')

    assert result.exit_code == 1, result.output
    assert 'Could not find latest Python version' in result.output


def test_update_python_version_invalid_hash_format(fake_repo, ddev, mocker):
    # Mock the constants that get imported by the upgrade script
    mocker.patch('ddev.repo.constants.PYTHON_VERSION_FULL', '3.13.7')
    mocker.patch('ddev.repo.constants.PYTHON_VERSION', '3.13')

    mocker.patch('ddev.cli.meta.scripts.upgrade_python.get_latest_python_version', return_value='3.13.9')
    # Hash validation happens inside get_python_sha256_hashes, so it raises ValueError
    mocker.patch(
        'ddev.cli.meta.scripts.upgrade_python.get_python_sha256_hashes',
        side_effect=ValueError('Invalid Linux SHA256 hash format from SBOM: not-a-valid-hash'),
    )

    result = ddev('meta', 'scripts', 'upgrade-python-version')

    assert result.exit_code == 1, result.output
    assert 'Failed to fetch' in result.output
    assert 'Invalid Linux SHA256 hash format' in result.output


class TestGetPbsReleaseInfo:
    def test_parses_sha256sums_and_returns_hashes(self, mocker):
        from ddev.cli.meta.scripts.upgrade_python import get_pbs_release_info

        mock_app = mocker.MagicMock()

        release_response = mocker.MagicMock()
        release_response.text = '{"tag_name": "20251215"}'

        sha_response = mocker.MagicMock()
        sha_response.text = _make_sha256sums('3.13.9', '20251215')
        sha_response.status_code = 200

        mocker.patch(
            'ddev.cli.meta.scripts.upgrade_python.httpx.get',
            side_effect=[release_response, sha_response],
        )

        result = get_pbs_release_info(mock_app, '3.13.9')

        assert result == {
            'release': '20251215',
            'aarch64': AARCH64_HASH,
            'x86_64': X86_64_HASH,
        }

    def test_returns_none_when_architecture_missing(self, mocker):
        from ddev.cli.meta.scripts.upgrade_python import get_pbs_release_info

        mock_app = mocker.MagicMock()

        release_response = mocker.MagicMock()
        release_response.text = '{"tag_name": "20251215"}'

        sha_response = mocker.MagicMock()
        sha_response.text = _make_sha256sums('3.13.9', '20251215', archs=('aarch64',))
        sha_response.status_code = 200

        mocker.patch(
            'ddev.cli.meta.scripts.upgrade_python.httpx.get',
            side_effect=[release_response, sha_response],
        )

        result = get_pbs_release_info(mock_app, '3.13.9')

        assert result is None


def test_upgrade_reports_error_when_pbs_release_unavailable(fake_repo, ddev, mocker):
    mocker.patch('ddev.repo.constants.PYTHON_VERSION_FULL', '3.13.7')
    mocker.patch('ddev.repo.constants.PYTHON_VERSION', '3.13')
    mocker.patch('ddev.cli.meta.scripts.upgrade_python.get_latest_python_version', return_value='3.13.9')
    mocker.patch(
        'ddev.cli.meta.scripts.upgrade_python.get_python_sha256_hashes',
        return_value={
            'linux_source_sha256': 'c4c066af19c98fb7835d473bebd7e23be84f6e9874d47db9e39a68ee5d0ce35c',
            'windows_amd64_sha256': '200ddff856bbff949d2cc1be42e8807c07538abd6b6966d5113a094cf628c5c5',
        },
    )
    mocker.patch('ddev.cli.meta.scripts.upgrade_python.get_pbs_release_info', return_value=None)

    result = ddev('meta', 'scripts', 'upgrade-python-version')

    assert result.exit_code == 1, result.output
    assert 'Could not find PBS release' in result.output


def test_upgrade_macos_reports_error_on_pattern_mismatch(tmp_path, mocker):
    from ddev.cli.meta.scripts.upgrade_python import upgrade_macos_python_version

    mock_app = mocker.MagicMock()
    mock_app.repo.path = tmp_path
    mock_tracker = mocker.MagicMock()

    workflow_dir = tmp_path / '.github' / 'workflows'
    workflow_dir.mkdir(parents=True)
    (workflow_dir / 'resolve-build-deps.yaml').write_text('name: Resolve build deps\njobs:\n  build: {}\n')

    mocker.patch(
        'ddev.cli.meta.scripts.upgrade_python.get_pbs_release_info',
        return_value={'release': '20251215', 'aarch64': AARCH64_HASH, 'x86_64': X86_64_HASH},
    )

    upgrade_macos_python_version(mock_app, '3.13.9', mock_tracker)

    mock_tracker.error.assert_called_once()
    assert 'Could not find PYTHON_PATCH in workflow file' in mock_tracker.error.call_args[1]['message']

# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


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

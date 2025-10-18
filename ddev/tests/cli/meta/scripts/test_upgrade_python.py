# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def setup_python_update_files(fake_repo):
    """Add PYTHON_VERSION_FULL and Dockerfiles to fake_repo."""
    # Update constants.py to include PYTHON_VERSION_FULL
    constants_file = fake_repo.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'
    content = constants_file.read_text()
    content += "PYTHON_VERSION_FULL = '3.13.7'\n"
    constants_file.write_text(content)

    # Create Linux ARM64 Dockerfile
    linux_aarch64_dir = fake_repo.path / '.builders' / 'images' / 'linux-aarch64'
    linux_aarch64_dir.mkdir(parents=True, exist_ok=True)
    (linux_aarch64_dir / 'Dockerfile').write_text("""FROM ubuntu:22.04

# Install Python
ENV PYTHON3_VERSION=3.13.7
RUN DOWNLOAD_URL="https://python.org/ftp/python/{{version}}/Python-{{version}}.tgz" \\
 VERSION="${PYTHON3_VERSION}" \\
 SHA256="6c9d80839cfa20024f34d9a6dd31ae2a9cd97ff5e980e969209746037a5153b2" \\
 bash install-from-source.sh

CMD ["/bin/bash"]
""")

    # Create Linux x86_64 Dockerfile
    linux_x86_64_dir = fake_repo.path / '.builders' / 'images' / 'linux-x86_64'
    linux_x86_64_dir.mkdir(parents=True, exist_ok=True)
    (linux_x86_64_dir / 'Dockerfile').write_text("""FROM ubuntu:22.04

# Install Python
ENV PYTHON3_VERSION=3.13.7
RUN DOWNLOAD_URL="https://python.org/ftp/python/{{version}}/Python-{{version}}.tgz" \\
 VERSION="${PYTHON3_VERSION}" \\
 SHA256="6c9d80839cfa20024f34d9a6dd31ae2a9cd97ff5e980e969209746037a5153b2" \\
 bash install-from-source.sh

CMD ["/bin/bash"]
""")

    # Create Windows Dockerfile
    windows_dockerfile_dir = fake_repo.path / '.builders' / 'images' / 'windows-x86_64'
    windows_dockerfile_dir.mkdir(parents=True, exist_ok=True)
    (windows_dockerfile_dir / 'Dockerfile').write_text("""FROM mcr.microsoft.com/windows/servercore:ltsc2022

# Install Python
ENV PYTHON_VERSION="3.13.7"
RUN powershell -Command " \\
    Invoke-WebRequest -OutFile python-$Env:PYTHON_VERSION-amd64.exe \\
        https://www.python.org/ftp/python/$Env:PYTHON_VERSION/python-$Env:PYTHON_VERSION-amd64.exe \\
        -Hash '48652a4e6af29c2f1fde2e2e6bbf3734a82ce3f577e9fd5c95c83f68e29e1eaa'"

CMD ["powershell"]
""")

    # Create macOS workflow file
    workflows_dir = fake_repo.path / '.github' / 'workflows'
    workflows_dir.mkdir(parents=True, exist_ok=True)
    (workflows_dir / 'resolve-build-deps.yaml').write_text("""name: Resolve build dependencies

on:
  workflow_dispatch:

env:
  PYTHON3_DOWNLOAD_URL: "https://www.python.org/ftp/python/3.13.7/python-3.13.7-macos11.pkg"

jobs:
  build:
    runs-on: macos-latest
    steps:
      - run: echo "test"
""")


def test_update_python_version_success(fake_repo, ddev, mocker):
    """Test successful Python version update."""
    setup_python_update_files(fake_repo)
    # Mock network calls
    mocker.patch('ddev.cli.meta.scripts.upgrade_python.get_latest_python_version', return_value='3.13.9')
    mocker.patch(
        'ddev.cli.meta.scripts.upgrade_python.get_python_sha256_hashes',
        return_value={
            'linux_source_sha256': 'c4c066af19c98fb7835d473bebd7e23be84f6e9874d47db9e39a68ee5d0ce35c',
            'windows_amd64_sha256': '200ddff856bbff949d2cc1be42e8807c07538abd6b6966d5113a094cf628c5c5',
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

    # Verify macOS workflow was updated
    workflow_file = fake_repo.path / '.github' / 'workflows' / 'resolve-build-deps.yaml'
    contents = workflow_file.read_text()
    assert 'python-3.13.9-macos11.pkg' in contents
    assert 'python-3.13.7-macos11.pkg' not in contents


def test_update_python_version_already_latest(fake_repo, ddev, mocker):
    setup_python_update_files(fake_repo)
    mocker.patch('ddev.cli.meta.scripts.upgrade_python.get_latest_python_version', return_value='3.13.7')

    result = ddev('meta', 'scripts', 'upgrade-python-version')

    assert result.exit_code == 0, result.output
    assert 'Already at latest Python version: 3.13.7' in result.output


def test_update_python_version_no_new_version_found(fake_repo, ddev, mocker):
    setup_python_update_files(fake_repo)
    mocker.patch('ddev.cli.meta.scripts.upgrade_python.get_latest_python_version', return_value=None)

    result = ddev('meta', 'scripts', 'upgrade-python-version')

    assert result.exit_code == 1, result.output
    assert 'Could not find latest Python version' in result.output


def test_update_python_version_invalid_hash_format(fake_repo, ddev, mocker):
    setup_python_update_files(fake_repo)
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

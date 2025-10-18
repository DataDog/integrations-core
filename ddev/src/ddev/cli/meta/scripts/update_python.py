# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

import click
import httpx
import orjson
import requests
from packaging.version import Version

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.validation.tracker import ValidationTracker

@click.command('update-python-version', short_help='Upgrade the Python version used in the repository.')
@click.pass_obj
def update_python_version(app: Application):
    """Upgrade the Python version used in the repository.

    Automatically detects the latest Python version, fetches official SHA256 hashes,
    and updates version references across:
    - ddev/src/ddev/repo/constants.py
    - .builders/images/*/Dockerfile (Linux and Windows)
    - .github/workflows/resolve-build-deps.yaml (macOS)

    \b
    `$ ddev meta scripts update-python-version`
    """
    from ddev.repo.constants import PYTHON_VERSION_FULL as current_version
    from ddev.repo.constants import PYTHON_VERSION as major_minor

    tracker = app.create_validation_tracker('Python version updates')
    
    # Check for new version
    latest_version = get_latest_python_version(app, major_minor)
    if latest_version is None:
        app.display_error(f"Could not find latest Python version for {major_minor}")
        app.abort()
    
    # Validate version string format for security (prevent injection)
    if not validate_version_string(latest_version):
        app.display_error(f"Invalid version format detected: {latest_version}")
        app.abort()
    
    if Version(latest_version) <= Version(current_version):
        app.display_info(f"Already at latest Python version: {current_version}")
        return
    
    app.display_info(f"Updating Python from {current_version} to {latest_version}")
    
    # Fetch hashes
    try:
        new_version_hashes = get_python_sha256_hashes(app, latest_version)
    except Exception as e:
        tracker.error(('SHA256 hashes',), message=f"Failed to fetch: {e}")
        tracker.display()
        app.abort()
    
    # Validate hashes
    if not validate_sha256(new_version_hashes.get('linux_source_sha256', '')):
        tracker.error(('SHA256 validation',), message="Invalid Linux SHA256 hash format")
    if not validate_sha256(new_version_hashes.get('windows_amd64_sha256', '')):
        tracker.error(('SHA256 validation',), message="Invalid Windows SHA256 hash format")
    
    if tracker.errors:
        tracker.display()
        app.abort()
    
    # Perform updates
    update_python_version_full_constant(app, latest_version, tracker)
    update_dockerfiles_python_version(app, latest_version, new_version_hashes, tracker)
    update_macos_python_version(app, latest_version, tracker)
    
    # Display results
    tracker.display()
    
    if tracker.errors:
        app.display_warning("Some updates failed. Please review the errors above.")
        app.abort()
    
    app.display_success(f"Python version updated from {current_version} to {latest_version}")

def validate_version_string(version: str) -> bool:
    """
    Validate that version string is safe and matches expected format.
    
    Args:
        version: Version string to validate
        
    Returns:
        True if valid, False otherwise
    """
    return bool(re.match(r'^\d+\.\d+\.\d+$', version))


def validate_sha256(hash_str: str) -> bool:
    """Validate SHA256 hash format (64 hex characters)."""
    return bool(re.match(r'^[0-9a-f]{64}$', hash_str))


def update_dockerfiles_python_version(
    app: Application, new_version: str, hashes: dict[str, str], tracker: ValidationTracker
):
    dockerfiles = [
        app.repo.path / '.builders' / 'images' / 'linux-aarch64' / 'Dockerfile',
        app.repo.path / '.builders' / 'images' / 'linux-x86_64' / 'Dockerfile',
        app.repo.path / '.builders' / 'images' / 'windows-x86_64' / 'Dockerfile',
    ]
    
    try:
        linux_sha = hashes['linux_source_sha256']
        windows_sha = hashes['windows_amd64_sha256']
    except KeyError as error:
        tracker.error(('Dockerfiles',), message=f'Missing SHA256 hash entry: {error}')
        return

    # Linux: ENV PYTHON3_VERSION=3.13.7 (no quotes, matches version at end of line)
    # Windows: ENV PYTHON_VERSION="3.13.7" (with quotes)
    linux_version_pattern = re.compile(r'(ENV PYTHON3_VERSION=)(\d+\.\d+\.\d+)$', re.MULTILINE)
    windows_version_pattern = re.compile(r'(ENV PYTHON_VERSION=")(\d+\.\d+\.\d+)(")', re.MULTILINE)

    # SHA256 patterns must match the Python-specific ones:
    # Linux: SHA256 that comes after VERSION="${PYTHON3_VERSION}"
    # Windows: -Hash in the same RUN block with python-$Env:PYTHON_VERSION-amd64.exe
    linux_sha_pattern = re.compile(
        r'VERSION="\$\{PYTHON3_VERSION\}"[^\n]*\n[^\n]*SHA256="([0-9a-f]+)"',
        re.MULTILINE
    )
    windows_sha_pattern = re.compile(
        r'python-\$Env:PYTHON_VERSION-amd64\.exe[^\n]*\n[^\n]*-Hash\s+\'([0-9a-f]+)\'',
        re.MULTILINE
    )

    for dockerfile in dockerfiles:
        if not dockerfile.exists():
            tracker.error((dockerfile.name,), message=f'File not found: {dockerfile}')
            continue
        
        try:
            content = dockerfile.read_text()
        except Exception as e:
            tracker.error((dockerfile.name,), message=f'Failed to read: {e}')
            continue

        is_windows = 'windows-x86_64' in dockerfile.parts
        version_pattern = windows_version_pattern if is_windows else linux_version_pattern
        sha_pattern = windows_sha_pattern if is_windows else linux_sha_pattern
        target_sha = windows_sha if is_windows else linux_sha

        def replace_version(match: re.Match[str]) -> str:
            if is_windows:
                prefix, _old_version, suffix = match.groups()
                return f'{prefix}{new_version}{suffix}'
            else:
                prefix, _old_version = match.groups()
                return f'{prefix}{new_version}'

        def replace_sha(match: re.Match[str]) -> str:
            # The entire match contains the old hash, replace just the hash part
            old_match = match.group(0)
            old_hash = match.group(1)
            return old_match.replace(old_hash, target_sha)

        # Helper to apply pattern substitution with error tracking
        def apply_substitution(pattern: re.Pattern, replace_func, error_msg: str) -> str | None:
            nonlocal content
            content, count = pattern.subn(replace_func, content, count=1)
            if count == 0:
                tracker.error((dockerfile.name,), message=error_msg)
                return None
            return content

        # Apply version update
        if apply_substitution(version_pattern, replace_version, 'Could not find Python version pattern') is None:
            continue

        # Apply SHA256 update
        if apply_substitution(sha_pattern, replace_sha, 'Could not find SHA256 pattern') is None:
            continue

        try:
            dockerfile.write_text(content)
            tracker.success()
        except Exception as e:
            tracker.error((dockerfile.name,), message=f'Failed to write: {e}')


def update_macos_python_version(app: Application, new_version: str, tracker: ValidationTracker):
    macos_python_file = app.repo.path / '.github' / 'workflows' / 'resolve-build-deps.yaml'
    
    if not macos_python_file.exists():
        tracker.error(('macOS workflow',), message=f'File not found: {macos_python_file}')
        return
    
    try:
        content = macos_python_file.read_text()
    except Exception as e:
        tracker.error(('macOS workflow',), message=f'Failed to read: {e}')
        return
    
    target_line = next((line for line in content.splitlines() if 'PYTHON3_DOWNLOAD_URL' in line), None)

    if target_line is None:
        tracker.error(('macOS workflow',), message='Could not find PYTHON3_DOWNLOAD_URL')
        return

    new_url = f'https://www.python.org/ftp/python/{new_version}/python-{new_version}-macos11.pkg'
    indent = target_line[: target_line.index('PYTHON3_DOWNLOAD_URL')]
    new_line = f'{indent}PYTHON3_DOWNLOAD_URL: "{new_url}"'

    if target_line == new_line:
        return

    updated_content = content.replace(target_line, new_line, 1)
    
    try:
        macos_python_file.write_text(updated_content)
        tracker.success()
    except Exception as e:
        tracker.error(('macOS workflow',), message=f'Failed to write: {e}')


def update_python_version_full_constant(app: Application, new_version: str, tracker: ValidationTracker):
    constants_file = app.repo.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'
    
    if not constants_file.exists():
        tracker.error(('constants.py',), message=f'File not found: {constants_file}')
        return
    
    try:
        content = constants_file.read_text()
    except Exception as e:
        tracker.error(('constants.py',), message=f'Failed to read: {e}')
        return

    prefix = 'PYTHON_VERSION_FULL = '
    target_line = next((line for line in content.splitlines() if line.startswith(prefix)), None)

    if target_line is None:
        tracker.error(('constants.py',), message='Could not find PYTHON_VERSION_FULL constant')
        return

    new_line = f"{prefix}'{new_version}'"
    if target_line == new_line:
        return

    updated_content = content.replace(target_line, new_line, 1)
    
    try:
        constants_file.write_text(updated_content)
        tracker.success()
    except Exception as e:
        tracker.error(('constants.py',), message=f'Failed to write: {e}')


def get_latest_python_version(app: Application, major_minor: str) -> str | None:
    """
    Get the latest Python version from python.org FTP directory.
    
    Args:
        major_minor: Python version in format "3.13"
    
    Returns:
        Latest version string (e.g., "3.13.1") or None if not found
    """
    url = "https://www.python.org/ftp/python/"
    
    try:
        # Explicitly verify SSL/TLS certificate
        response = requests.get(url, timeout=30, verify=True)
        response.raise_for_status()
    except requests.RequestException as e:
        app.display_error(f"Error fetching Python versions: {e}")
        return None
    
    # Parse directory listing for version folders
    # Looking for patterns like: <a href="3.13.0/">3.13.0/</a>
    pattern = rf'<a href="({re.escape(major_minor)}\.\d+)/">'
    versions = []
    
    for line in response.text.split("\n"):
        match = re.search(pattern, line)
        if match:
            version_str = match.group(1)
            try:
                versions.append(Version(version_str))
            except Exception:
                # Skip invalid versions
                continue
    
    if not versions:
        return None
    
    # Sort and return the latest version
    versions.sort()
    return str(versions[-1])


def get_python_sha256_hashes(app: Application, version: str) -> dict[str, str]:
    """
    Fetch SHA256 hashes for Python release artifacts using SBOM files.
    
    Python.org provides SBOM (Software Bill of Materials) files in SPDX JSON format
    for each release artifact. These files contain SHA256 checksums.
    
    Args:
        version: Python version string (e.g., "3.13.7")
    
    Returns:
        Dictionary with SHA256 hashes:
        {
            'linux_source_sha256': '<64-char hex hash>',
            'windows_amd64_sha256': '<64-char hex hash>'
        }
    
    Raises:
        ValueError: If version format is invalid
        RuntimeError: If SBOM files cannot be fetched or parsed
    """
    # Validate version format before using in URL construction (security)
    if not validate_version_string(version):
        raise ValueError(f"Invalid version format: {version}")
    
    # Steps:
    # 1. Construct SBOM URLs for the files we need:
    #    - Linux source tarball:
    #      https://www.python.org/ftp/python/{version}/Python-{version}.tgz.spdx.json
    #    - Windows AMD64 installer:
    #      https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe.spdx.json
    SBOM_URLS = [
        f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz.spdx.json",
        f"https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe.spdx.json"
    ]
    # 2. Download and parse each SBOM JSON file
    async def get_sbom_data(client, url):
        try:
            # Explicitly verify SSL/TLS certificates
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            data = orjson.loads(response.text)
            
            # Validate SBOM structure
            if not isinstance(data, dict):
                raise ValueError(f"Invalid SBOM format: expected dict, got {type(data)}")
            if 'packages' not in data:
                raise ValueError("Invalid SBOM format: missing 'packages' field")
            
            return data.get('packages', [])
        except Exception as e:
            raise RuntimeError(f'Error processing URL {url}: {e}') from e

    async def fetch_sbom_data(urls):
        # Create client with explicit SSL verification
        async with httpx.AsyncClient(verify=True) as client:
            return await asyncio.gather(*(get_sbom_data(client, url) for url in urls))
    
    sbom_packages = asyncio.run(fetch_sbom_data(SBOM_URLS))

    # Find the CPython package in the SBOM packages
    linux_cpython_package = next((package for package in sbom_packages[0] if package.get('name') == "CPython"), None)
    windows_cpython_package = next((package for package in sbom_packages[1] if package.get('name') == "CPython"), None)
    
    if linux_cpython_package is None:
        raise ValueError("Could not find CPython package in Linux SBOM")
    if windows_cpython_package is None:
        raise ValueError("Could not find CPython package in Windows SBOM")
    
    # Find the SHA256 checksum in the CPython package checksums
    linux_checksums = linux_cpython_package.get('checksums', [])
    windows_checksums = windows_cpython_package.get('checksums', [])
    
    linux_checksum = next((checksum for checksum in linux_checksums if checksum.get('algorithm') == "SHA256"), None)
    windows_checksum = next((checksum for checksum in windows_checksums if checksum.get('algorithm') == "SHA256"), None)
    
    if linux_checksum is None:
        raise ValueError("Could not find SHA256 checksum in Linux SBOM")
    if windows_checksum is None:
        raise ValueError("Could not find SHA256 checksum in Windows SBOM")
    
    # Extract hash values and validate format
    linux_hash = linux_checksum.get('checksumValue', '')
    windows_hash = windows_checksum.get('checksumValue', '')
    
    if not validate_sha256(linux_hash):
        raise ValueError(f"Invalid Linux SHA256 hash format from SBOM: {linux_hash}")
    if not validate_sha256(windows_hash):
        raise ValueError(f"Invalid Windows SHA256 hash format from SBOM: {windows_hash}")
    
    return {
        'linux_source_sha256': linux_hash,
        'windows_amd64_sha256': windows_hash
    }

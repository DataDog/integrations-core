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
from packaging.version import Version

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.validation.tracker import ValidationTracker

# Python.org URLs
PYTHON_FTP_URL = "https://www.python.org/ftp/python/"
PYTHON_SBOM_LINUX_URL_TEMPLATE = "https://www.python.org/ftp/python/{version}/Python-{version}.tgz.spdx.json"
PYTHON_SBOM_WINDOWS_URL_TEMPLATE = "https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe.spdx.json"

# Python Build Standalone (PBS) - used for macOS
# https://github.com/astral-sh/python-build-standalone
PBS_LATEST_RELEASE_URL = "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
PBS_SHA256SUMS_URL_TEMPLATE = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/{release}/SHA256SUMS"
)

# Regex patterns for Dockerfile updates
# Linux: ENV PYTHON3_VERSION=3.13.7 (no quotes, matches version at end of line)
LINUX_VERSION_PATTERN = re.compile(r'(ENV PYTHON3_VERSION=)(\d+\.\d+\.\d+)$', re.MULTILINE)
# Windows: ENV PYTHON_VERSION="3.13.7" (with quotes)
WINDOWS_VERSION_PATTERN = re.compile(r'(ENV PYTHON_VERSION=")(\d+\.\d+\.\d+)(")', re.MULTILINE)

# SHA256 patterns must match the Python-specific ones:
# Linux: SHA256 that comes after VERSION="${PYTHON3_VERSION}"
LINUX_SHA_PATTERN = re.compile(r'VERSION="\$\{PYTHON3_VERSION\}"[^\n]*\n[^\n]*SHA256="([0-9a-f]+)"', re.MULTILINE)
# Windows: -Hash in the same RUN block with python-$Env:PYTHON_VERSION-amd64.exe
WINDOWS_SHA_PATTERN = re.compile(
    r'python-\$Env:PYTHON_VERSION-amd64\.exe[^\n]*\n[^\n]*-Hash\s+\'([0-9a-f]+)\'', re.MULTILINE
)


@click.command('upgrade-python-version', short_help='Upgrade the Python version used in the repository.')
@click.pass_obj
def upgrade_python_version(app: Application):
    """Upgrade the Python version used in the repository.

    Automatically detects the latest Python version, fetches official SHA256 hashes,
    and updates version references across:
    - ddev/src/ddev/repo/constants.py
    - .builders/images/*/Dockerfile (Linux and Windows)
    - .github/workflows/resolve-build-deps.yaml (macOS)

    \b
    `$ ddev meta scripts upgrade-python-version`
    """
    from ddev.repo.constants import PYTHON_VERSION as major_minor
    from ddev.repo.constants import PYTHON_VERSION_FULL as current_version

    tracker = app.create_validation_tracker('Python version upgrades')

    # Check for new version
    latest_version = get_latest_python_version(app, major_minor)
    if not latest_version:
        app.display_error(f"Could not find latest Python version for {major_minor}")
        app.abort()
        return  # Unreachable but helps type checker

    if Version(latest_version) <= Version(current_version):
        app.display_info(f"Already at latest Python version: {current_version}")
        return

    app.display_info(f"Updating Python from {current_version} to {latest_version}")

    # Fetch and validate hashes (validation happens inside get_python_sha256_hashes)
    try:
        new_version_hashes = get_python_sha256_hashes(app, latest_version)
    except Exception as e:
        tracker.error(('SHA256 hashes',), message=f"Failed to fetch: {e}")
        tracker.display()
        app.abort()
        return  # Unreachable but helps type checker

    # Perform updates
    upgrade_dockerfiles_python_version(app, latest_version, new_version_hashes, tracker)
    upgrade_macos_python_version(app, latest_version, tracker)
    upgrade_python_version_full_constant(app, latest_version, tracker)

    # Display results
    tracker.display()

    if tracker.errors:
        app.display_warning("Some updates failed. Please review the errors above.")
        app.abort()
        return  # Unreachable but helps type checker

    app.display_success(f"Python version upgraded from {current_version} to {latest_version}")


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
    return bool(re.match(r'^[0-9A-Fa-f]{64}$', hash_str))


def read_file_safely(file_path, file_label: str, tracker: ValidationTracker) -> str | None:
    """
    Read file with error handling.

    Args:
        file_path: Path to the file
        file_label: Label for error messages
        tracker: Validation tracker for error reporting

    Returns:
        File content as string, or None if an error occurred
    """
    if not file_path.exists():
        tracker.error((file_label,), message=f'File not found: {file_path}')
        return None

    try:
        return file_path.read_text()
    except Exception as e:
        tracker.error((file_label,), message=f'Failed to read: {e}')
        return None


def write_file_safely(file_path, content: str, file_label: str, tracker: ValidationTracker) -> bool:
    """
    Write file with error handling.

    Args:
        file_path: Path to the file
        content: Content to write
        file_label: Label for error messages
        tracker: Validation tracker for success/error reporting

    Returns:
        True if successful, False otherwise
    """
    try:
        file_path.write_text(content)
        tracker.success()
        return True
    except Exception as e:
        tracker.error((file_label,), message=f'Failed to write: {e}')
        return False


def extract_sha256_from_sbom(packages: list, platform_name: str) -> str:
    """
    Extract SHA256 hash from SBOM packages.

    Args:
        packages: List of packages from SBOM
        platform_name: Platform name for error messages (e.g., "Linux", "Windows")

    Returns:
        SHA256 hash string

    Raises:
        ValueError: If package, checksum, or hash format is invalid
    """
    cpython_package = next((pkg for pkg in packages if pkg.get('name') == "CPython"), None)
    if cpython_package is None:
        raise ValueError(f"Could not find CPython package in {platform_name} SBOM")

    checksums = cpython_package.get('checksums', [])
    checksum = next((cs for cs in checksums if cs.get('algorithm') == "SHA256"), None)
    if checksum is None:
        raise ValueError(f"Could not find SHA256 checksum in {platform_name} SBOM")

    hash_value = checksum.get('checksumValue', '')
    if not validate_sha256(hash_value):
        raise ValueError(f"Invalid {platform_name} SHA256 hash format from SBOM: {hash_value}")

    return hash_value


def upgrade_dockerfiles_python_version(
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

    for dockerfile in dockerfiles:
        dockerfile_content = read_file_safely(dockerfile, dockerfile.name, tracker)
        if dockerfile_content is None:
            continue

        is_windows = 'windows-x86_64' in dockerfile.parts
        version_pattern = WINDOWS_VERSION_PATTERN if is_windows else LINUX_VERSION_PATTERN
        sha_pattern = WINDOWS_SHA_PATTERN if is_windows else LINUX_SHA_PATTERN
        target_sha = windows_sha if is_windows else linux_sha

        def replace_version(match: re.Match[str], _is_windows=is_windows) -> str:
            if _is_windows:
                prefix, _old_version, suffix = match.groups()
                return f'{prefix}{new_version}{suffix}'
            else:
                prefix, _old_version = match.groups()
                return f'{prefix}{new_version}'

        def replace_sha(match: re.Match[str], _target_sha=target_sha) -> str:
            # The entire match contains the old hash, replace just the hash part
            old_match = match.group(0)
            old_hash = match.group(1)
            return old_match.replace(old_hash, _target_sha)

        # Helper to apply pattern substitution with error tracking
        def apply_substitution(pattern: re.Pattern, replace_func, error_msg: str, _dockerfile=dockerfile) -> bool:
            nonlocal dockerfile_content
            dockerfile_content, count = pattern.subn(replace_func, dockerfile_content, count=1)
            if count == 0:
                tracker.error((_dockerfile.name,), message=error_msg)
                return False
            return True

        # Apply version update
        if not apply_substitution(version_pattern, replace_version, 'Could not find Python version pattern'):
            continue

        # Apply SHA256 update
        if not apply_substitution(sha_pattern, replace_sha, 'Could not find SHA256 pattern'):
            continue

        write_file_safely(dockerfile, dockerfile_content, dockerfile.name, tracker)


def upgrade_macos_python_version(app: Application, new_version: str, tracker: ValidationTracker):
    """
    Update macOS Python version in the workflow file.

    The workflow uses Python Build Standalone (PBS) from Astral. Updates PYTHON_PATCH,
    PBS_RELEASE, and the SHA256 hashes for both macOS architectures.
    """
    workflow_file = app.repo.path / '.github' / 'workflows' / 'resolve-build-deps.yaml'
    content = read_file_safely(workflow_file, 'macOS workflow', tracker)
    if content is None:
        return

    new_patch = new_version.split('.')[-1]

    # Get the latest PBS release and SHA256 hashes
    pbs_info = get_pbs_release_info(app, new_version)
    if pbs_info is None:
        tracker.error(
            ('macOS workflow',),
            message=f'Could not find PBS release with Python {new_version}. '
            'A new PBS release may not be available yet.',
        )
        return

    # Define replacements: (pattern, new_value)
    replacements = [
        (r'^(\s*PYTHON_PATCH:\s*)\d+\s*$', rf'\g<1>{new_patch}'),
        (r'^(\s*PBS_RELEASE:\s*)\d+\s*$', rf"\g<1>{pbs_info['release']}"),
        (r'^(\s*PBS_SHA256__aarch64:\s*)[0-9a-f]+\s*$', rf"\g<1>{pbs_info['aarch64']}"),
        (r'^(\s*PBS_SHA256__x86_64:\s*)[0-9a-f]+\s*$', rf"\g<1>{pbs_info['x86_64']}"),
    ]

    for pattern, replacement in replacements:
        content, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
        if count == 0:
            tracker.error(('macOS workflow',), message=f'Could not find pattern: {pattern}')
            return

    write_file_safely(workflow_file, content, 'macOS workflow', tracker)


def upgrade_python_version_full_constant(app: Application, new_version: str, tracker: ValidationTracker):
    constants_file = app.repo.path / 'ddev' / 'src' / 'ddev' / 'repo' / 'constants.py'

    constants_content = read_file_safely(constants_file, 'constants.py', tracker)
    if constants_content is None:
        return

    prefix = 'PYTHON_VERSION_FULL = '
    target_line = next((line for line in constants_content.splitlines() if line.startswith(prefix)), None)

    if target_line is None:
        tracker.error(('constants.py',), message='Could not find PYTHON_VERSION_FULL constant')
        return

    new_line = f"{prefix}'{new_version}'"
    if target_line == new_line:
        app.display_info(f"Python version in constants.py is already at {new_version}")
        return

    updated_content = constants_content.replace(target_line, new_line, 1)
    write_file_safely(constants_file, updated_content, 'constants.py', tracker)


def get_latest_python_version(app: Application, major_minor: str) -> str | None:
    """
    Get the latest Python version from python.org FTP directory.

    Args:
        major_minor: Python version in format "3.13"

    Returns:
        Latest version string (e.g., "3.13.1") or None if not found
    """
    try:
        # Explicitly verify SSL/TLS certificate
        response = httpx.get(PYTHON_FTP_URL, timeout=30, verify=True)
        response.raise_for_status()
    except httpx.RequestException as e:
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


def get_pbs_release_info(app: Application, python_version: str) -> dict[str, str] | None:
    """
    Get the latest PBS release info with SHA256 hashes for the specified Python version.

    Returns dict with 'release', 'aarch64', 'x86_64' keys, or None if not found.
    """
    try:
        # Get latest PBS release tag
        response = httpx.get(PBS_LATEST_RELEASE_URL, timeout=30)
        response.raise_for_status()
        release = orjson.loads(response.text).get('tag_name')
        if not release:
            return None

        # Fetch SHA256SUMS file and extract hashes for our target files
        sha_response = httpx.get(PBS_SHA256SUMS_URL_TEMPLATE.format(release=release), timeout=30, follow_redirects=True)
        if sha_response.status_code != 200:
            return None

        hashes = {'release': release}
        for arch in ('aarch64', 'x86_64'):
            filename = f'cpython-{python_version}+{release}-{arch}-apple-darwin-install_only_stripped.tar.gz'
            for line in sha_response.text.splitlines():
                if filename in line:
                    sha_hash = line.split()[0]
                    if validate_sha256(sha_hash):
                        hashes[arch] = sha_hash
                    break

        # Verify we found both architectures
        if 'aarch64' not in hashes or 'x86_64' not in hashes:
            return None

        return hashes

    except httpx.RequestException as e:
        app.display_warning(f"Error fetching PBS release info: {e}")
        return None


def get_python_sha256_hashes(app: Application, version: str) -> dict[str, str]:
    """
    Fetch SHA256 hashes for Python release artifacts using SBOM files.

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

    # Construct SBOM URLs for the files we need
    sbom_urls = [
        PYTHON_SBOM_LINUX_URL_TEMPLATE.format(version=version),
        PYTHON_SBOM_WINDOWS_URL_TEMPLATE.format(version=version),
    ]

    # Download and parse each SBOM JSON file
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
        async with httpx.AsyncClient(verify=True) as client:
            return await asyncio.gather(*(get_sbom_data(client, url) for url in urls))

    sbom_packages = asyncio.run(fetch_sbom_data(sbom_urls))

    # Extract SHA256 hashes from SBOM packages
    linux_hash = extract_sha256_from_sbom(sbom_packages[0], 'Linux')
    windows_hash = extract_sha256_from_sbom(sbom_packages[1], 'Windows')

    return {'linux_source_sha256': linux_hash, 'windows_amd64_sha256': windows_hash}

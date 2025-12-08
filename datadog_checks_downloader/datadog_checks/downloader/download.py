# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import collections
import hashlib
import logging
import logging.config
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import boto3
import yaml

from packaging.version import parse as parse_version
from tuf.ngclient import Updater

from .exceptions import (
    DuplicatePackage,
    InconsistentSimpleIndex,
    MissingVersions,
    NoSuchDatadogPackage,
    NoSuchDatadogPackageVersion,
    PythonVersionMismatch,
    TargetNotFoundError,
)

# After we import everything we need, shut off all existing loggers.
logging.config.dictConfig({'disable_existing_loggers': True, 'version': 1})


# CONSTANTS.
here = os.path.abspath(os.path.dirname(__file__))
REPOSITORIES_DIR = os.path.join(here, 'data')
REPOSITORY_DIR = 'repo'
REPOSITORY_URL_PREFIX = 'https://test-public-integration-wheels.s3.eu-north-1.amazonaws.com'
ROOT_LAYOUTS = {'core': '7.core.root.layout', 'extras': '1.extras.root.layout'}
DEFAULT_ROOT_LAYOUT_TYPE = 'core'


# Global variables.
logger = logging.getLogger(__name__)


class TUFDownloader:
    def __init__(
        self,
        repository_url_prefix=REPOSITORY_URL_PREFIX,
        root_layout_type=DEFAULT_ROOT_LAYOUT_TYPE,
        verbose=0,
        disable_verification=False,
    ):
        # 0 => 60 (effectively /dev/null)
        # 1 => 50 (CRITICAL)
        # 2 => 40 (ERROR)
        # 3 => 30 (WARNING)
        # 4 => 20 (INFO)
        # 5 => 10 (DEBUG)
        remainder = min(verbose, 5) % 6
        level = (6 - remainder) * 10
        assert level in range(10, 70, 10), level
        logging.basicConfig(format='%(levelname)-8s: %(message)s', level=level)

        self.__root_layout_type = root_layout_type
        self.__root_layout = ROOT_LAYOUTS[self.__root_layout_type]
        self.__repository_url_prefix = repository_url_prefix

        self.__disable_verification = disable_verification
        self.__current_version = None
        self.__current_wheel_href = None
        self.__current_pointer_path = None

        if self.__disable_verification:
            logger.warning(
                'Running with TUF verification disabled. Integrity is only protected with TLS (HTTPS).'
            )

        # NOTE: The directory where the targets for *this* repository is
        # cached. We hard-code this keep this to a subdirectory dedicated to
        # this repository.
        self.__targets_dir = os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR, 'targets')

        # NOTE: Build a TUF updater which stores metadata in (1) the given
        # directory, and (2) uses the following mirror configuration,
        # respectively.
        # NOTE: This updater will store files under:
        # os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR)
        self.__updater = Updater(
            metadata_dir=os.path.join(REPOSITORIES_DIR, REPOSITORY_DIR, 'metadata'),
            metadata_base_url=f'{repository_url_prefix}/metadata/',
            target_base_url=f'{repository_url_prefix}/',
            target_dir=self.__targets_dir,
        )

        # Increase requests timeout.
        # There's no officially supported way to do this without either writing our own
        # fetcher from scratch or relying on internals. We're choosing the latter for now.
        # - https://github.com/theupdateframework/python-tuf/blob/v2.0.0/tuf/ngclient/updater.py#L99
        # - https://github.com/theupdateframework/python-tuf/blob/v2.0.0/tuf/ngclient/_internal/requests_fetcher.py#L49
        self.__updater._fetcher.socket_timeout = 60

        # NOTE: Update to the latest top-level role metadata only ONCE, so that
        # we use the same consistent snapshot to download targets.
        self.__updater.refresh()

    def __compute_target_paths(self, target_relpath):
        # The path used to query TUF needs to be a path-relative-URL string
        # (https://url.spec.whatwg.org/#path-relative-url-string), which means the path
        # separator *must* be `/` and only `/`.
        # This is a defensive measure to make things work even if the provided `target_relpath`
        # is a platform-specific filesystem path.
        tuf_target_path = pathlib.PurePath(target_relpath).as_posix()
        target_abspath = os.path.join(self.__targets_dir, tuf_target_path)

        return tuf_target_path, target_abspath

    def _download_without_tuf_in_toto(self, target_relpath):
        assert isinstance(self.__updater._target_base_url, str), self.__updater._target_base_url

        tuf_target_path, target_abspath = self.__compute_target_paths(target_relpath)

        # reproducing how the "self.__updater.download_target" method computes the URL
        target_base_url = self.__updater._target_base_url
        full_url = target_base_url + ('/' if not target_base_url.endswith('/') else '') + tuf_target_path

        try:
            with urllib.request.urlopen(full_url) as resp:
                os.makedirs(os.path.dirname(target_abspath), exist_ok=True)
                with open(target_abspath, 'wb') as dest:
                    dest.write(resp.read())
        except urllib.error.HTTPError as err:
            logger.error('GET %s: %s', full_url, err)
            raise

        return target_abspath

    def _download_with_tuf(self, target_relpath):
        tuf_target_path, target_abspath = self.__compute_target_paths(target_relpath)

        target = self.__updater.get_targetinfo(tuf_target_path)
        if target is None:
            raise TargetNotFoundError(f'Target at {tuf_target_path} not found')

        local_relpath = self.__updater.find_cached_target(target, target_abspath)

        # Either the target has not been updated...
        if local_relpath:
            logger.debug('%s has not been updated', tuf_target_path)
        # or, it has been updated, in which case we download the new version
        else:
            os.makedirs(os.path.dirname(target_abspath), exist_ok=True)
            self.__updater.download_target(target, target_abspath)

        logger.info('TUF verified %s', tuf_target_path)

        return target_abspath, target


    def __download_wheel_from_pointer(self, pointer_abspath, standard_distribution_name):
        """Download wheel using pointer file.

        Args:
            pointer_abspath: Local path to downloaded pointer file
            standard_distribution_name: Package name

        Returns:
            Absolute path to downloaded wheel file
        """
        from urllib.parse import urlparse

        # Parse pointer file
        with open(pointer_abspath, 'rb') as f:
            pointer_bytes = f.read()

        pointer_content = yaml.safe_load(pointer_bytes)
        pointer = pointer_content.get('pointer', {})

        wheel_uri = pointer.get('uri', '')
        wheel_digest = pointer.get('digest', '')
        wheel_name = pointer.get('name', standard_distribution_name)
        wheel_version = pointer.get('version', self.__current_version)

        if not wheel_uri or not wheel_digest:
            raise ValueError(f"Invalid pointer file: missing uri or digest")

        # Rewrite wheel URI for local development if using local MinIO
        # Check if repository URL is localhost (local MinIO)
        if 'localhost' in self.__repository_url_prefix:
            # Extract the path from the production URI
            # Example: https://test-public-integration-wheels.s3.eu-north-1.amazonaws.com/simple/... → simple/...
            from urllib.parse import urlparse
            production_parsed = urlparse(wheel_uri)
            wheel_path = production_parsed.path.lstrip('/')

            # Reconstruct using local MinIO endpoint
            wheel_uri = f'{self.__repository_url_prefix}/{wheel_path}'
            logger.debug(f'Rewrote wheel URI for local development: {wheel_uri}')

        # Extract wheel filename from URI
        wheel_filename = wheel_uri.split('/')[-1]

        # Download wheel from S3 with authentication
        logger.info(f'Downloading wheel from: {wheel_uri}')
        wheel_abspath = os.path.join(self.__targets_dir, 'simple', standard_distribution_name, wheel_filename)
        os.makedirs(os.path.dirname(wheel_abspath), exist_ok=True)

        try:
            # Parse S3 URI to extract bucket and key
            parsed = urlparse(wheel_uri)

            # Check if this is a local MinIO URL (localhost)
            if parsed.hostname and 'localhost' in parsed.hostname:
                # Local MinIO format: http://localhost:9000/bucket-name/path/to/file
                # Extract bucket and key from path
                path_parts = parsed.path.lstrip('/').split('/', 1)
                if len(path_parts) < 2:
                    raise ValueError(f"Invalid local MinIO URI format: {wheel_uri}")

                bucket_name = path_parts[0]
                s3_key = path_parts[1]
                endpoint_url = f"{parsed.scheme}://{parsed.netloc}"

                logger.debug(f'Parsed local MinIO URI: bucket={bucket_name}, key={s3_key}, endpoint={endpoint_url}')

                # Use boto3 with MinIO credentials
                s3_client = boto3.client(
                    's3',
                    endpoint_url=endpoint_url,
                    aws_access_key_id='minioadmin',
                    aws_secret_access_key='minioadmin',
                    region_name='us-east-1'  # MinIO doesn't care about region
                )
            else:
                # Production AWS S3
                # Example: https://test-public-integration-wheels.s3.eu-north-1.amazonaws.com/simple/datadog-postgres/wheel.whl
                # Extract bucket name from hostname (format: bucket.s3.region.amazonaws.com)
                bucket_name = parsed.hostname.split('.')[0]

                # Extract S3 key (path without leading /)
                s3_key = parsed.path.lstrip('/')

                # Extract region from hostname if present
                if '.s3.' in parsed.hostname and '.amazonaws.com' in parsed.hostname:
                    region = parsed.hostname.split('.s3.')[1].split('.amazonaws.com')[0]
                else:
                    region = None

                logger.debug(f'Parsed S3 URI: bucket={bucket_name}, key={s3_key}, region={region}')

                # Use boto3 to download with AWS credentials
                s3_client = boto3.client('s3', region_name=region)

            response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            wheel_bytes = response['Body'].read()

            # Verify digest
            actual_digest = hashlib.sha256(wheel_bytes).hexdigest()
            if actual_digest != wheel_digest:
                raise ValueError(
                    f"Wheel digest mismatch: expected {wheel_digest}, got {actual_digest}"
                )

            # Save wheel
            with open(wheel_abspath, 'wb') as f:
                f.write(wheel_bytes)

            logger.info(f'Wheel verified and saved: {wheel_abspath}')
            return wheel_abspath

        except Exception as err:
            logger.error('Failed to download wheel from %s: %s', wheel_uri, err)
            raise

    def download(self, target_relpath):
        """
        Returns:
            If download over TUF is successful, this function will
            return the complete filepath to the desired wheel.
        """
        # Extract package name from path like 'simple/datadog-postgres/...'
        path_parts = target_relpath.split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'simple':
            standard_distribution_name = path_parts[1]

            # Use stored pointer path if available (from pointer-based discovery)
            if self.__current_pointer_path:
                pointer_relpath = self.__current_pointer_path
            else:
                # Fall back to constructing pointer path (backward compatibility)
                # Format: pointers/{package}/{package}-{version}.pointer
                pointer_filename = f"{standard_distribution_name}-{self.__current_version}.pointer"
                pointer_relpath = f"pointers/{standard_distribution_name}/{pointer_filename}"

            logger.info(f'Downloading pointer file: {pointer_relpath}')

            # Download pointer via TUF
            if self.__disable_verification:
                pointer_abspath = self._download_without_tuf_in_toto(pointer_relpath)
            else:
                pointer_abspath, _ = self._download_with_tuf(pointer_relpath)

            # Download wheel using pointer
            wheel_abspath = self.__download_wheel_from_pointer(pointer_abspath, standard_distribution_name)

            # Always return the posix version of the path for consistency across platforms
            return pathlib.Path(wheel_abspath).as_posix()

        # Fallback for non-wheel targets (shouldn't happen in normal operation)
        logger.warning(f'Unexpected target path format: {target_relpath}')
        if self.__disable_verification:
            target_abspath = self._download_without_tuf_in_toto(target_relpath)
        else:
            target_abspath, _ = self._download_with_tuf(target_relpath)
        return pathlib.Path(target_abspath).as_posix()

    def __get_versions_from_pointers(self, standard_distribution_name):
        """Get available versions from pointer files in TUF targets.

        Args:
            standard_distribution_name: Normalized package name (e.g., 'datadog-postgres')

        Returns:
            Dict mapping version strings to pointer file paths
            Example: {'23.2.0': 'pointers/datadog-postgres/datadog-postgres-23.2.0.pointer'}
        """
        versions = {}

        # Access the trusted targets metadata from the updater
        # The _trusted_set contains the verified metadata after refresh()
        logger.debug(f"Checking for pointer files for package: {standard_distribution_name}")
        logger.debug(f"Updater has _trusted_set: {hasattr(self.__updater, '_trusted_set')}")

        if hasattr(self.__updater, '_trusted_set'):
            logger.debug(f"_trusted_set has targets: {hasattr(self.__updater._trusted_set, 'targets')}")

            if hasattr(self.__updater._trusted_set, 'targets'):
                targets_metadata = self.__updater._trusted_set.targets
                logger.debug(f"targets_metadata type: {type(targets_metadata)}")
                logger.debug(f"targets_metadata.targets type: {type(targets_metadata.targets)}")
                logger.debug(f"Number of targets: {len(targets_metadata.targets)}")

                # Filter pointer files for this package
                # Pattern: pointers/{package}/{package}-{version}.pointer
                pointer_prefix = f'pointers/{standard_distribution_name}/'
                expected_filename_prefix = f'{standard_distribution_name}-'
                logger.debug(f"Looking for pointer prefix: {pointer_prefix}")

                for target_path in targets_metadata.targets:
                    logger.debug(f"Checking target: {target_path}")
                    if target_path.startswith(pointer_prefix) and target_path.endswith('.pointer'):
                        # Extract version from pointer file path
                        filename = target_path.split('/')[-1]  # Get last part
                        logger.debug(f"Found pointer file: {target_path}, filename: {filename}")

                        # Remove standard distribution name prefix and .pointer suffix
                        # Example: "datadog-postgres-23.2.0.pointer" → "23.2.0"
                        if filename.startswith(expected_filename_prefix):
                            version = filename[len(expected_filename_prefix):-len('.pointer')]
                            versions[version] = target_path
                            logger.debug(f"Extracted version: {version}")

        if not versions:
            logger.error(f"No versions found for {standard_distribution_name}")
            raise NoSuchDatadogPackage(standard_distribution_name)

        logger.info(f"Found versions: {versions}")
        return versions

    def __get_versions(self, standard_distribution_name):
        """Get available versions for a package.

        If TUF is enabled, fetches versions from pointer files in TUF targets.
        Otherwise, falls back to simple index HTML for backward compatibility.

        Returns:
            When TUF is enabled: {version: pointer_path}
            When TUF is disabled: {version: {python_tag: wheel_filename}}
        """
        # TUF enabled: Use pointer files from TUF targets
        if not self.__disable_verification:
            return self.__get_versions_from_pointers(standard_distribution_name)

        # TUF disabled: Fall back to simple index HTML (backward compatibility)
        index_relpath = 'simple/{}/index.html'.format(standard_distribution_name)
        # https://www.python.org/dev/peps/pep-0491/#escaping-and-unicode
        wheel_distribution_name = re.sub('[^\\w\\d.]+', '_', standard_distribution_name, re.UNICODE)  # noqa: B034
        pattern = "<a href='(" + wheel_distribution_name + "-(.*?)-(.*?)-none-any\\.whl)'>(.*?)</a><br />"
        # version: {python_tag: href}
        wheels = collections.defaultdict(dict)

        index_abspath = self._download_without_tuf_in_toto(index_relpath)

        with open(index_abspath) as simple_index:
            for line in simple_index:
                match = re.match(pattern, line)

                if match:
                    href, version, python_tag, text = match.groups()

                    if href != text:
                        raise InconsistentSimpleIndex(href, text)
                    else:
                        python_tags = wheels[version]
                        if python_tag in python_tags:
                            raise DuplicatePackage(standard_distribution_name, version, python_tag)
                        python_tags[python_tag] = href

        return wheels

    def get_wheel_relpath(self, standard_distribution_name, version=None, ignore_python_version=False):
        """
        Returns:
            If download over TUF is successful, this function will return the
            latest known version of the Datadog integration.
        """
        wheels = self.__get_versions(standard_distribution_name)

        if not wheels:
            raise MissingVersions(standard_distribution_name)

        if not version:
            # Go through all wheels and remove alphas, betas and rcs and pick the latest version
            # https://packaging.pypa.io/en/latest/version.html
            version = str(max(parse_version(v) for v in wheels.keys() if not parse_version(v).is_prerelease))

        # Check if using pointer-based discovery (TUF enabled) or simple index (TUF disabled)
        # When TUF enabled: wheels[version] is a pointer path string
        # When TUF disabled: wheels[version] is a dict {python_tag: href}
        version_data = wheels.get(version)
        if not version_data:
            raise NoSuchDatadogPackageVersion(standard_distribution_name, version)

        # Handle pointer-based discovery (TUF enabled)
        if isinstance(version_data, str):
            # version_data is a pointer path
            self.__current_pointer_path = version_data
            self.__current_version = version

            # Construct wheel filename assuming py3
            # Pattern: {package_underscore}-{version}-py3-none-any.whl
            package_underscore = standard_distribution_name.replace('-', '_')
            wheel_filename = f'{package_underscore}-{version}-py3-none-any.whl'
            self.__current_wheel_href = wheel_filename

            return 'simple/{}/{}'.format(standard_distribution_name, wheel_filename)

        # Handle simple index-based discovery (TUF disabled)
        else:
            python_tags = version_data
            self.__current_pointer_path = None

            # First, try finding the pure Python wheel for this version.
            this_python = 'py{}'.format(sys.version_info[0])
            href = python_tags.get(this_python)

            # Otherwise, try finding the universal Python wheel for this version.
            if not href:
                href = python_tags.get('py2.py3')

            # Otherwise, fuhgedaboutit.
            if not href:
                if ignore_python_version:
                    href = list(python_tags.values())[0]
                else:
                    raise PythonVersionMismatch(standard_distribution_name, version, this_python, python_tags)

            # Store version for use in pointer-based download
            self.__current_version = version
            self.__current_wheel_href = href

            return 'simple/{}/{}'.format(standard_distribution_name, href)

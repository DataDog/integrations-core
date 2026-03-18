from __future__ import annotations

import argparse
import email.message
import json
import re
import time
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from zipfile import ZipFile

from google.cloud import storage

if TYPE_CHECKING:
    from google.cloud.storage.bucket import Bucket as GCSBucket

BUCKET_NAME = 'deps-agent-int-datadoghq-com'
STORAGE_URL = 'https://agent-int-packages.datadoghq.com'
BUILDER_DIR = Path(__file__).parent
REPO_DIR = BUILDER_DIR.parent
RESOLUTION_DIR = REPO_DIR / '.deps'
LOCK_FILE_DIR = RESOLUTION_DIR / 'resolved'
DIRECT_DEP_FILE = REPO_DIR / 'agent_requirements.in'
WORKFLOW_FILE = REPO_DIR / '.github/workflows/resolve-build-deps.yaml'
CACHE_CONTROL = 'public, max-age=15'
VALID_PROJECT_NAME = re.compile(r'^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$', re.IGNORECASE)
UNNORMALIZED_PROJECT_NAME_CHARS = re.compile(r'[-_.]+')
CURRENT_PYTHON_VERSION = "3.13"

def is_valid_project_name(project_name: str) -> bool:
    # https://peps.python.org/pep-0508/#names
    return VALID_PROJECT_NAME.search(project_name) is not None


def normalize_project_name(name: str) -> str:
    # https://peps.python.org/pep-0503/#normalized-names
    return UNNORMALIZED_PROJECT_NAME_CHARS.sub('-', name).lower()


def extract_metadata(wheel: Path) -> email.message.Message:
    with ZipFile(str(wheel)) as zip_archive:
        for path in zip_archive.namelist():
            root = path.split('/', 1)[0]
            if root.endswith('.dist-info'):
                dist_info_dir = root
                break
        else:
            message = f'Could not find the `.dist-info` directory in wheel: {wheel.name}'
            raise RuntimeError(message)

        try:
            with zip_archive.open(f'{dist_info_dir}/METADATA') as zip_file:
                metadata_file_contents = zip_file.read().decode('utf-8')
        except KeyError:
            message = f'Could not find a `METADATA` file in the `{dist_info_dir}` directory'
            raise RuntimeError(message) from None

    return email.message_from_string(metadata_file_contents)


def display_message_block(message: str) -> None:
    divider = f'+{"-" * (len(message) + 2)}+'
    print(divider)
    print(f'| {message} |')
    print(divider)


def timestamp_build_number() -> int:
    """Produce a numeric timestamp to use as build numbers"""
    return int(time.strftime('%Y%m%d%H%M%S'))


def hash_file(path: Path) -> str:
    """Calculate the hash of the file pointed at by `path`"""
    with path.open('rb') as f:
        return sha256(f.read()).hexdigest()


def hash_directory(path: Path) -> str:
    """Compute a combined SHA256 hash of all files in a directory."""
    h = sha256()
    for file_path in sorted(path.rglob('*'), key=lambda p: p.relative_to(path)):
        if file_path.is_file():
            h.update(file_path.relative_to(path).as_posix().encode())
            h.update(file_path.read_bytes())
    return h.hexdigest()


def compute_input_hashes() -> dict[str, str]:
    """Compute SHA256 hashes for all dependency resolution inputs."""
    try:
        return {
            'agent_requirements.in': hash_file(DIRECT_DEP_FILE),
            '.github/workflows/resolve-build-deps.yaml': hash_file(WORKFLOW_FILE),
            '.builders': hash_directory(BUILDER_DIR),
        }
    except FileNotFoundError as e:
        raise RuntimeError(f'Missing dependency resolution input: {e}') from e


def _build_number_of_wheel(wheel_info: dict) -> int:
    """Extract the build number from wheel information."""
    wheel_name = PurePosixPath(wheel_info['name']).stem
    _name, _version, *build_number, _python_tag, _abi_tag, _platform_tag = wheel_name.split('-')
    return int(build_number[0]) if build_number else -1


def collect_and_validate_wheels(wheel_dir: Path) -> list[tuple[str, email.message.Message, Path]]:
    """Collect all wheels from a directory and validate their metadata."""
    upload_data: list[tuple[str, email.message.Message, Path]] = []
    for wheel in wheel_dir.iterdir():
        project_metadata = extract_metadata(wheel)
        project_name = project_metadata['Name']
        if not is_valid_project_name(project_name):
            message = f'Invalid project name `{project_name}` found in wheel: {wheel.name}'
            raise RuntimeError(message)

        print(f'Project name: {project_name}')
        upload_data.append((normalize_project_name(project_name), project_metadata, wheel))

    upload_data.sort()
    return upload_data


def process_wheel_for_upload(wheel: Path, artifact_type: str, project_name: str, project_metadata: email.message.Message, bucket: Bucket, prefix: str) -> tuple[str, str | None]:
    """Process a single wheel and determine if it needs to be uploaded."""
    padding = ' ' * (len(prefix) + 1)
    print(f'{prefix} Name: {project_metadata["Name"]}')
    print(f'{padding}Version: {project_metadata["Version"]}')

    sha256_digest = hash_file(wheel)
    index_url = f'{STORAGE_URL}/{artifact_type}/{project_name}'

    if artifact_type == 'external':
        artifact_name = wheel.name
        blob_path = f'{artifact_type}/{project_name}/{artifact_name}'

        if bucket.blob_exists(blob_path):
            print(f'{prefix} {project_name}=={project_metadata["Version"]} already exists')
            metadata = bucket.get_blob_metadata(blob_path)
            existing_sha256 = metadata['sha256']
            return f'{project_name} @ {index_url}/{artifact_name}#sha256={existing_sha256}', None
        else:
            return f'{project_name} @ {index_url}/{artifact_name}#sha256={sha256_digest}', artifact_name
    else:
        name, version, *_build_tag, python_tag, abi_tag, platform_tag = wheel.stem.split('-')
        existing_wheels = bucket.find_matching_wheels(
            match_glob=(f'{artifact_type}/{project_name}/'
                        f'{name}-{version}*-{python_tag}-{abi_tag}-{platform_tag}.whl')
        )

        if existing_wheels:
            most_recent_wheel = max(existing_wheels, key=_build_number_of_wheel)
            if most_recent_wheel['metadata']['sha256'] == sha256_digest:
                print(f'{prefix} {project_name}=={project_metadata["Version"]} already exists '
                      'with the same hash')
                existing_artifact_name = PurePosixPath(most_recent_wheel['name']).name
                return f'{project_name} @ {index_url}/{existing_artifact_name}#sha256={sha256_digest}', None

        build_number = timestamp_build_number()
        artifact_name = f'{name}-{version}-{build_number}-{python_tag}-{abi_tag}-{platform_tag}.whl'
        return f'{project_name} @ {index_url}/{artifact_name}#sha256={sha256_digest}', artifact_name


def upload_wheel_to_bucket(wheel: Path, artifact_type: str, project_name: str, artifact_name: str, project_metadata: email.message.Message, bucket: Bucket, padding: str):
    """Upload a wheel file to the bucket."""
    print(f'{padding}Artifact: {artifact_name}')
    blob_path = f'{artifact_type}/{project_name}/{artifact_name}'
    sha256_digest = hash_file(wheel)
    requires_python = project_metadata.get('Requires-Python', '').replace('<', '&lt;').replace('>', '&gt;')
    bucket.upload_file(str(wheel), blob_path, metadata={'requires-python': requires_python, 'sha256': sha256_digest})


def generate_artifact_listings(artifact_types: set[str], bucket: Bucket):
    """Generate HTML listings for all artifact types."""
    for artifact_type in sorted(artifact_types):
        display_message_block(f'Updating {artifact_type} listing')

        root_listing_lines = [
            '<!DOCTYPE html>',
            '<html>',
            '  <body>',
            '    <h1>Agent integrations dependencies</h1>',
        ]
        project_artifacts: dict[str, list[dict]] = {}
        for wheel_info in bucket.list_wheels_with_prefix(prefix=f'{artifact_type}/'):
            project_artifacts.setdefault(wheel_info['project'], []).append(wheel_info)

        for project, artifacts in sorted(project_artifacts.items()):
            print(project)
            root_listing_lines.append(f'    <a href="{project}/">{project}</a><br>')

            artifacts.sort(key=lambda w: w['name'].casefold())
            project_listing_lines = [
                '<!DOCTYPE html>',
                '<html>',
                '  <body>',
                f'    <h1>{project}</h1>',
            ]

            for artifact in artifacts:
                requires_python = artifact['metadata']['requires-python']
                sha256_digest = artifact['metadata']['sha256']
                artifact_name = artifact['name'].split('/')[2]
                attribute = f' data-requires-python="{requires_python}"' if requires_python else ''

                project_listing_lines.append(
                    f'    <a href="{artifact_name}#sha256={sha256_digest}"{attribute}>{artifact_name}</a><br>'
                )

            project_listing_lines.extend(('  </body>', '</html>', ''))
            bucket.upload_string(
                '\n'.join(project_listing_lines),
                f'{artifact_type}/{project}/',
                content_type='text/html',
                cache_control=CACHE_CONTROL
            )

        root_listing_lines.extend(('  </body>', '</html>', ''))
        bucket.upload_string(
            '\n'.join(root_listing_lines),
            f'{artifact_type}/',
            content_type='text/html',
            cache_control=CACHE_CONTROL
        )


class Bucket:
    """
    Wrap interactions with Google Storage Bucket.

    This makes for easier testing and separates bucket interaction from the business logic.
    """

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self._client: storage.Client | None = None
        self._bucket: GCSBucket | None = None

    def _get_bucket(self) -> GCSBucket:
        """Lazily initialize and return the bucket."""
        if self._bucket is None:
            if self._client is None:
                self._client = storage.Client()
            self._bucket = self._client.bucket(self.bucket_name)
        return self._bucket

    def blob_exists(self, path: str) -> bool:
        """Check if a blob exists."""
        return self._get_bucket().blob(path).exists()

    def get_blob_metadata(self, path: str) -> dict:
        """Get metadata for a blob."""
        blob = self._get_bucket().blob(path)
        blob.reload()
        return blob.metadata

    def find_matching_wheels(self, match_glob: str) -> list[dict]:
        """Find wheels matching a glob pattern and return their information."""
        wheels = []
        for blob in self._get_bucket().list_blobs(match_glob=match_glob):
            blob.reload()
            wheels.append({
                'name': blob.name,
                'metadata': blob.metadata
            })
        return wheels

    def list_wheels_with_prefix(self, prefix: str) -> list[dict]:
        """List all wheel files under a prefix and return their information."""
        wheels = []
        for blob in self._get_bucket().list_blobs(prefix=prefix):
            if blob.name.endswith('.whl'):
                blob.reload()
                project = blob.name.split('/')[1]
                wheels.append({
                    'name': blob.name,
                    'project': project,
                    'metadata': blob.metadata
                })
        return wheels

    def upload_file(self, local_path: str, blob_path: str, metadata: dict | None = None) -> None:
        """Upload a file to the bucket with optional metadata."""
        blob = self._get_bucket().blob(blob_path)
        blob.upload_from_filename(local_path)
        if metadata:
            blob.metadata = metadata
            blob.patch()

    def upload_string(self, content: str, blob_path: str, content_type: str = 'text/plain', cache_control: str | None = None) -> None:
        """Upload string content to the bucket with optional cache control."""
        blob = self._get_bucket().blob(blob_path)
        blob.upload_from_string(content, content_type=content_type)
        if cache_control:
            blob.cache_control = cache_control
            blob.patch()


def generate_lockfiles(targets_dir, lockfiles):
    targets_dir = Path(targets_dir)
    LOCK_FILE_DIR.mkdir(parents=True, exist_ok=True)
    with RESOLUTION_DIR.joinpath('metadata.json').open('w', encoding='utf-8') as f:
        inputs = compute_input_hashes()
        contents = json.dumps(
            {
                'inputs': inputs,
                'sha256': inputs['agent_requirements.in'],
            },
            indent=2,
            sort_keys=True,
        )
        f.write(f'{contents}\n')

    image_digests = {}
    for target_name, lockfile_lines in lockfiles.items():
        # The lockfiles contain the major.minor Python version
        # so that the Agent can transition safely
        lock_file = LOCK_FILE_DIR / f'{target_name}_{CURRENT_PYTHON_VERSION}.txt'
        lock_file.write_text('\n'.join(lockfile_lines), encoding='utf-8')

        # these `image_digest` files are generated in the 'Save new image digest'
        # step of the github workflow
        if (image_digest_file := targets_dir / target_name / 'image_digest').is_file():
            image_digests[target_name] = image_digest_file.read_text(encoding='utf-8').strip()

    with RESOLUTION_DIR.joinpath('image_digests.json').open('w', encoding='utf-8') as f:
        contents = json.dumps(image_digests, indent=2, sort_keys=True)
        f.write(f'{contents}\n')


def upload(targets_dir: Path, bucket: Bucket | None = None) -> dict[str, list[str]]:
    bucket = bucket or Bucket(BUCKET_NAME)
    artifact_types: set[str] = set()
    lockfiles = {}

    for target in Path(targets_dir).iterdir():
        display_message_block(f'Target {target.name}')
        for python_version in target.iterdir():
            if not python_version.name.startswith('py'):
                continue

            lockfile_lines = []
            display_message_block(f'Python version {python_version.name}')

            wheel_dir = python_version / 'wheels'
            for entry in sorted(wheel_dir.iterdir(), key=lambda p: p.name):
                artifact_type = entry.name
                artifact_types.add(artifact_type)
                display_message_block(f'Processing {artifact_type} wheels')

                upload_data = collect_and_validate_wheels(entry)
                queued = len(upload_data)

                for i, (project_name, project_metadata, wheel) in enumerate(upload_data, start=1):
                    prefix = f'({i}/{queued})'
                    padding = ' ' * (len(prefix) + 1)

                    lockfile_entry, artifact_name = process_wheel_for_upload(
                        wheel, artifact_type, project_name, project_metadata, bucket, prefix
                    )
                    lockfile_lines.append(lockfile_entry)

                    if artifact_name:
                        upload_wheel_to_bucket(
                            wheel, artifact_type, project_name, artifact_name, project_metadata, bucket, padding
                        )

            lockfile_lines.append('')
            lockfiles[target.name] = lockfile_lines

    generate_artifact_listings(artifact_types, bucket)
    return lockfiles

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='builder', allow_abbrev=False)
    parser.add_argument('targets_dir')
    args = parser.parse_args()
    lockfiles = upload(args.targets_dir)
    generate_lockfiles(args.targets_dir, lockfiles)

from __future__ import annotations

import argparse
import email
import json
import re
import time
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Iterator
from zipfile import ZipFile

from google.cloud import storage

if TYPE_CHECKING:
    from google.cloud.storage.blob import Blob

BUCKET_NAME = 'deps-agent-int-datadoghq-com'
STORAGE_URL = 'https://agent-int-packages.datadoghq.com'
BUILDER_DIR = Path(__file__).parent
REPO_DIR = BUILDER_DIR.parent
RESOLUTION_DIR = REPO_DIR / '.deps'
LOCK_FILE_DIR = RESOLUTION_DIR / 'resolved'
DIRECT_DEP_FILE = REPO_DIR / 'agent_requirements.in'
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


def extract_metadata(wheel: Path) -> email.Message:
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


def _build_number_of_wheel_blob(wheel_path: Blob) -> int:
    """Extract the build number from a blob object representing a wheel."""
    wheel_name = PurePosixPath(wheel_path.name).stem
    _name, _version, *build_number, _python_tag, _abi_tag, _platform_tag = wheel_name.split('-')
    return int(build_number[0]) if build_number else -1


def generate_lockfiles(targets_dir, lockfiles):
    targets_dir = Path(targets_dir)
    LOCK_FILE_DIR.mkdir(parents=True, exist_ok=True)
    with RESOLUTION_DIR.joinpath('metadata.json').open('w', encoding='utf-8') as f:
        contents = json.dumps(
            {
                'sha256': sha256(DIRECT_DEP_FILE.read_bytes()).hexdigest(),
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


def upload(targets_dir):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
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

                upload_data: list[tuple[str, email.Message, Path]] = []
                for wheel in entry.iterdir():
                    project_metadata = extract_metadata(wheel)
                    project_name = project_metadata['Name']
                    if not is_valid_project_name(project_name):
                        message = f'Invalid project name `{project_name}` found in wheel: {wheel.name}'
                        raise RuntimeError(message)

                    print(f'Project name: {project_name}')
                    upload_data.append((normalize_project_name(project_name), project_metadata, wheel))

                queued = len(upload_data)
                upload_data.sort()

                for i, (project_name, project_metadata, wheel) in enumerate(upload_data, start=1):
                    prefix = f'({i}/{queued})'
                    padding = ' ' * (len(prefix) + 1)
                    print(f'{prefix} Name: {project_metadata["Name"]}')
                    print(f'{padding}Version: {project_metadata["Version"]}')

                    sha256_digest = hash_file(wheel)
                    index_url = f'{STORAGE_URL}/{artifact_type}/{project_name}'
                    if artifact_type == 'external':
                        artifact_name = wheel.name
                        # https://agent-int-packages.datadoghq.com/external/cffi/cffi-1.17.1-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

                        artifact = bucket.blob(f'{artifact_type}/{project_name}/{artifact_name}')

                        # PyPI artifacts never change, so we don't need to upload them again.
                        if artifact.exists():
                            print(f'{prefix} {project_name}=={project_metadata["Version"]} already exists')
                            artifact.reload()
                            existing_sha256 = artifact.metadata['sha256']
                            lockfile_lines.append(f'{project_name} @ {index_url}/{artifact_name}#sha256={existing_sha256}')
                            continue
                        else:
                            lockfile_lines.append(f'{project_name} @ {index_url}/{artifact_name}#sha256={sha256_digest}')

                    else:
                        # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
                        name, version, *_build_tag, python_tag, abi_tag, platform_tag = wheel.stem.split('-')
                        existing_wheels = list(bucket.list_blobs(
                            match_glob=(f'{artifact_type}/{project_name}/'
                                        f'{name}-{version}*-{python_tag}-{abi_tag}-{platform_tag}.whl'),
                        ))

                        if existing_wheels:
                            most_recent_wheel = max(existing_wheels, key=_build_number_of_wheel_blob)
                            # Don't upload if it's the same file
                            if most_recent_wheel.metadata['sha256'] == sha256_digest:
                                print(f'{prefix} {project_name}=={project_metadata["Version"]} already exists '
                                    'with the same hash')
                                existing_artifact_name = PurePosixPath(most_recent_wheel.name).name # GCS blob name use forward slashes
                                lockfile_lines.append(f'{project_name} @ {index_url}/{existing_artifact_name}#sha256={sha256_digest}')
                                continue

                        # If we get here, that means that this is a new dependency
                        # and we need to upload the wheel for built artifacts
                        build_number = timestamp_build_number()
                        artifact_name = f'{name}-{version}-{build_number}-{python_tag}-{abi_tag}-{platform_tag}.whl'
                        artifact = bucket.blob(f'{artifact_type}/{project_name}/{artifact_name}')
                        lockfile_lines.append(f'{project_name} @ {index_url}/{artifact_name}#sha256={sha256_digest}')

                    # For built OR external artifacts
                    # only get here if we need to upload the wheel
                    print(f'{padding}Artifact: {artifact_name}')
                    artifact.upload_from_filename(str(wheel))
                    requires_python = project_metadata.get('Requires-Python', '').replace('<', '&lt;').replace('>', '&gt;') # noqa: 501
                    artifact.metadata = {'requires-python': requires_python, 'sha256': sha256_digest}
                    artifact.patch()

            lockfile_lines.append('')
            lockfiles[target.name] = lockfile_lines

    for artifact_type in sorted(artifact_types):
        display_message_block(f'Updating {artifact_type} listing')

        root_listing_lines = [
            '<!DOCTYPE html>',
            '<html>',
            '  <body>',
            '    <h1>Agent integrations dependencies</h1>',
        ]
        project_artifacts: dict[str, list[Blob]] = {}
        for blob in bucket.list_blobs(prefix=f'{artifact_type}/'):
            if blob.name.endswith('.whl'):
                project_artifacts.setdefault(blob.name.split('/')[1], []).append(blob)

        for project, artifacts in sorted(project_artifacts.items()):
            print(project)
            root_listing_lines.append(f'    <a href="{project}/">{project}</a><br>')

            artifacts.sort(key=lambda b: b.name.casefold())
            project_listing_lines = [
                '<!DOCTYPE html>',
                '<html>',
                '  <body>',
                f'    <h1>{project}</h1>',
            ]

            for artifact in artifacts:
                artifact.reload()
                requires_python = artifact.metadata['requires-python']
                sha256_digest = artifact.metadata['sha256']
                artifact_name = artifact.name.split('/')[2]
                attribute = f' data-requires-python="{requires_python}"' if requires_python else ''

                project_listing_lines.append(
                    f'    <a href="{artifact_name}#sha256={sha256_digest}"{attribute}>{artifact_name}</a><br>'
                )

            project_listing_lines.extend(('  </body>', '</html>', ''))
            project_listing = bucket.blob(f'{artifact_type}/{project}/')
            project_listing.upload_from_string('\n'.join(project_listing_lines), content_type='text/html')
            project_listing.cache_control = CACHE_CONTROL
            project_listing.patch()

        root_listing_lines.extend(('  </body>', '</html>', ''))
        root_listing = bucket.blob(f'{artifact_type}/')
        root_listing.upload_from_string('\n'.join(root_listing_lines), content_type='text/html')
        root_listing.cache_control = CACHE_CONTROL
        root_listing.patch()
    return lockfiles

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='builder', allow_abbrev=False)
    parser.add_argument('targets_dir')
    args = parser.parse_args()
    lockfiles = upload(args.targets_dir)
    generate_lockfiles(args.targets_dir, lockfiles)

# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Script to update test data.

It downloads a minimal subset of files from the actual online repository which is
enough to test downloading an integration. The files are saved in zip files under
tests/data.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urljoin
from urllib.request import urlopen
from zipfile import ZipFile

REPOSITORY_BASE_URL = 'https://dd-integrations-core-wheels-build-stable.datadoghq.com/'
INTEGRATION = 'active-directory'
INTEGRATION_VERSION = '1.10.0'
ZIP_FILENAME = f'datadog-{INTEGRATION}-{INTEGRATION_VERSION}.zip'
TARGET_DIR = Path(__file__).parent.parent / 'data'


def main():
    with TemporaryDirectory() as tempdir:
        tempdir = Path(tempdir)

        files_to_zip = set()
        versioned_metadata_files = {}
        # Matches each naked target path to a list of paths including all known hashes
        hashed_target_files = {}

        def download_file(relative_url):
            """Download the file at the given `relative_url` and store its path."""
            url = urljoin(REPOSITORY_BASE_URL, relative_url)
            destination = tempdir / relative_url
            destination.parent.mkdir(parents=True, exist_ok=True)

            print(f'Downloading {relative_url}')

            with open(destination, 'wb') as out_file:
                out_file.write(urlopen(url).read())

            files_to_zip.add(relative_url)

        def versioned(metadata_file):
            # If we know this is a versioned file, get that instead
            return versioned_metadata_files.get(metadata_file, metadata_file)

        def filenames_from_metadata(metadata_file):
            metadata = load_json(tempdir / 'metadata.staged' / versioned(metadata_file))

            for filename, meta in metadata['signed']['meta'].items():
                version = meta['version']
                full_name = f'{version}.{filename}'
                versioned_metadata_files[filename] = full_name
                yield f'metadata.staged/{full_name}'

        def filenames_for_target(metadata_file, target):
            metadata = load_json(tempdir / 'metadata.staged' / versioned(metadata_file))

            target_data = metadata['signed']['targets'][target]

            yield from hashed_target_files[target]
            for name in target_data['custom'].get('in-toto', []):
                yield from hashed_target_files[name]

        def load_target_filenames(metadata_file):
            """Populate dictionary with hash-including filenames from the given file."""
            metadata = load_json(tempdir / metadata_file)

            for target, target_data in metadata['signed']['targets'].items():
                for hash_ in target_data['hashes'].values():
                    target_path = Path(target)
                    target_with_hash = 'targets' / target_path.parent / f'{hash_}.{target_path.name}'
                    hashed_target_files.setdefault(target, []).append(str(target_with_hash))

        def zip_files(filename):
            """Write `files_to_zip` to a zip file."""
            print(f'Zipping files into {filename}...')
            with ZipFile(TARGET_DIR / filename, 'w') as zip_file:
                for file_ in files_to_zip:
                    zip_file.write(tempdir / file_, arcname=file_)

        # We first need to grab the timestamp file to begin finding all the files we need.
        download_file('metadata.staged/timestamp.json')

        for filename in filenames_from_metadata('timestamp.json'):
            download_file(filename)

        signer_file = f'wheels-signer-{INTEGRATION[0]}.json'

        for filename in filenames_from_metadata('snapshot.json'):
            # Skip wheel signers for wheels other than the one we want
            if 'wheels-signer-' in filename and not filename.endswith(signer_file):
                continue

            download_file(filename)
            load_target_filenames(filename)

        # Download required files for sample integration
        for filename in filenames_for_target(signer_file, f'simple/datadog-{INTEGRATION}/index.html'):
            download_file(filename)

        download_file(f'targets/simple/datadog-{INTEGRATION}/index.html')

        wheel_name = f'datadog_{INTEGRATION.replace("-", "_")}-{INTEGRATION_VERSION}-py2.py3-none-any.whl'
        download_file(f'targets/simple/datadog-{INTEGRATION}/{wheel_name}')

        for filename in filenames_for_target(signer_file, f'simple/datadog-{INTEGRATION}/{wheel_name}'):
            download_file(filename)

        # Grab latest in toto X.core.root.layout
        latest_in_toto_root_layout = max(
            filename for filename in hashed_target_files if filename.endswith('.core.root.layout')
        )
        for filename in filenames_for_target('targets.json', latest_in_toto_root_layout):
            download_file(filename)

        zip_files(ZIP_FILENAME)

        print('Done!')


def load_json(filename):
    with open(filename) as f:
        return json.load(f)


if __name__ == '__main__':
    main()

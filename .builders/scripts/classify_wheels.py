import argparse
import shutil
import time
from functools import cache
from hashlib import sha256
from pathlib import Path

import urllib3
from utils import extract_metadata, iter_wheels, normalize_project_name


@cache
def get_wheel_hashes(project) -> dict[str, str]:
    retry_wait = 2
    while True:
        try:
            response = urllib3.request(
                'GET',
                f'https://pypi.org/simple/{project}',
                headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            )
        except urllib3.exceptions.HTTPError as e:
            err_msg = f'Failed to fetch hashes for `{project}`: {e}'
        else:
            if response.status == 200:
                break

            err_msg = f'Failed to fetch hashes for `{project}`, status code: {response.status}'

        print(err_msg)
        print(f'Retrying in {retry_wait} seconds')
        time.sleep(retry_wait)
        retry_wait *= 2
        continue

    data = response.json()
    return {
        file['filename']: file['hashes']['sha256']
        for file in data['files']
        if file['filename'].endswith('.whl') and 'sha256' in file['hashes']
    }


def wheel_was_built(wheel: Path) -> bool:
    project_metadata = extract_metadata(wheel)
    project_name = normalize_project_name(project_metadata['Name'])
    wheel_hashes = get_wheel_hashes(project_name)
    if wheel.name not in wheel_hashes:
        return True

    file_hash = sha256(wheel.read_bytes()).hexdigest()
    return file_hash != wheel_hashes[wheel.name]


def classify_wheels(source_dir: str, built_dir: str, external_dir: str) -> None:
    for wheel in iter_wheels(source_dir):
        if wheel_was_built(wheel):
            shutil.move(wheel, built_dir)
        else:
            shutil.move(wheel, external_dir)


def main():
    parser = argparse.ArgumentParser("Classifies wheels into built and external depending on the hash of the wheel")
    parser.add_argument('--source-dir', required=True)
    parser.add_argument('--built-dir', required=True)
    parser.add_argument('--external-dir', required=True)
    args = parser.parse_args()

    classify_wheels(args.source_dir, args.built_dir, args.external_dir)


if __name__ == '__main__':
    main()
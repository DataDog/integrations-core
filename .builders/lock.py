from __future__ import annotations

import argparse
import json
import shutil
from hashlib import sha256
from pathlib import Path

BUILDER_DIR = Path(__file__).parent
REPO_DIR = BUILDER_DIR.parent
RESOLUTION_DIR = REPO_DIR / '.deps'
LOCK_FILE_DIR = RESOLUTION_DIR / 'resolved'
DIRECT_DEP_FILE = REPO_DIR / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data' / 'agent_requirements.in'


def main():
    parser = argparse.ArgumentParser(prog='builder', allow_abbrev=False)
    parser.add_argument('targets_dir')
    args = parser.parse_args()

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
    for target in Path(args.targets_dir).iterdir():
        for python_version in target.iterdir():
            if python_version.name.startswith('py'):
                lock_file = python_version / 'frozen.txt'
                shutil.copyfile(lock_file, LOCK_FILE_DIR / f'{target.name}_{python_version.name}.txt')

        if (image_digest_file := target / 'image_digest').is_file():
            image_digests[target.name] = image_digest_file.read_text(encoding='utf-8').strip()

    with BUILDER_DIR.joinpath('image_digests.json').open('w', encoding='utf-8') as f:
        contents = json.dumps(image_digests, indent=2, sort_keys=True)
        f.write(f'{contents}\n')


if __name__ == '__main__':
    main()

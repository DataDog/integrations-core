from __future__ import annotations

import argparse
import json
import re
import shutil
from hashlib import sha256
from pathlib import Path

BUILDER_DIR = Path(__file__).parent
REPO_DIR = BUILDER_DIR.parent
WORKFLOW_FILE = REPO_DIR / '.github' / 'workflows' / 'build-deps.yml'
RESOLUTION_DIR = REPO_DIR / '.deps'
LOCK_FILE_DIR = RESOLUTION_DIR / 'resolved'
DIRECT_DEP_FILE = REPO_DIR / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data' / 'agent_requirements.in'


def main():
    parser = argparse.ArgumentParser(prog='builder', allow_abbrev=False)
    parser.add_argument('targets_dir')
    args = parser.parse_args()

    LOCK_FILE_DIR.mkdir(parents=True, exist_ok=True)
    with RESOLUTION_DIR.joinpath('metadata.json').open('w', encoding='utf-8') as f:
        metadata_contents = json.dumps(
            {
                'sha256': sha256(DIRECT_DEP_FILE.read_bytes()).hexdigest(),
            },
            indent=2,
            sort_keys=True,
        )
        f.write(f'{metadata_contents}\n')

    workflow_contents = WORKFLOW_FILE.read_text(encoding='utf-8')
    for target in Path(args.targets_dir).iterdir():
        for python_version in target.iterdir():
            if python_version.name.startswith('py'):
                lock_file = python_version / 'frozen.txt'
                shutil.copyfile(lock_file, LOCK_FILE_DIR / f'{target.name}_{python_version.name}.txt')

        image_digest_file = target / 'image_digest'
        if not image_digest_file.is_file():
            continue

        match = re.search(rf'^\s+image: {target.name}$\s^\s+digest: (.+)$', workflow_contents, flags=re.MULTILINE)
        if not match:
            raise RuntimeError(f'Could not find image digest for {target}')

        original_block = match.group(0)
        new_block = original_block.replace(match.group(1), image_digest_file.read_text(encoding='utf-8').strip())
        workflow_contents = workflow_contents.replace(original_block, new_block)

    WORKFLOW_FILE.write_text(workflow_contents, encoding='utf-8')


if __name__ == '__main__':
    main()

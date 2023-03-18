"""
This script requires Python 3.11 or later and must not use any external dependencies.
"""
# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path
from typing import Any

if sys.version_info[:2] >= (3, 11):
    import tomllib
# TODO: remove this once ddev drops versions less than 3.11
else:
    import tomli as tomllib

# https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idoutputs
OUTPUT_LIMIT = 1024 * 1024

# https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#using-a-matrix-strategy
JOB_LIMIT = 256

TESTABLE_FILE_PATTERNS = (
    'assets/configuration/**/*',
    'tests/**/*',
    '*.py',
    'hatch.toml',
    'pyproject.toml',
)
NON_TESTABLE_FILES = {'auto_conf.yaml', 'agent_requirements.in'}
DISPLAY_ORDER_OVERRIDE = {
    _d: _i
    for _i, _d in enumerate(
        (
            'ddev',
            'datadog_checks_base',
            'datadog_checks_dev',
            'datadog_checks_downloader',
        )
    )
}
PLATFORM_NAMES = {'linux': 'Linux', 'windows': 'Windows', 'macos': 'macOS'}
PLATFORM_TO_OS = {
    # https://github.com/actions/runner-images/blob/main/images/linux/Ubuntu2204-Readme.md
    'linux': 'ubuntu-22.04',
    # https://github.com/actions/runner-images/blob/main/images/win/Windows2022-Readme.md
    'windows': 'windows-2022',
    # https://github.com/actions/runner-images/blob/main/images/macos/macos-12-Readme.md
    'macos': 'macos-12',
}


@lru_cache(maxsize=None)
def read_manifest(root: Path, target: str) -> dict:
    manifest_path = root / target / 'manifest.json'
    if not manifest_path.is_file():
        return {}

    return json.loads(manifest_path.read_text(encoding='utf-8'))


def normalize_job_name(job_name: str) -> str:
    # The job name is sometimes used to construct unique file paths, so we must replace characters that are reserved on
    # Windows, see: https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file#naming-conventions
    return re.sub(r'[<>:"/\\|?*]', '_', job_name)


def is_git_warning_line(line: str) -> bool:
    return line.startswith('warning: ') or 'original line endings' in line


def git(*args) -> str:
    try:
        process = subprocess.run(
            ['git', *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', check=True
        )
    except subprocess.CalledProcessError as e:
        raise OSError(f'{str(e)[:-1]}:\n{e.output}') from None

    return process.stdout


def get_changed_files(*, ref: str, local: bool) -> list[str]:
    changed_files = set()

    # Committed e.g.:
    # A   relative/path/to/file.added
    # M   relative/path/to/file.modified
    for line in git('diff', '--name-status', f'{ref}...').splitlines():
        if not is_git_warning_line(line):
            changed_files.add(line.split(maxsplit=1)[1])

    if local:
        # Tracked
        for line in git('diff', '--name-only', 'HEAD').splitlines():
            if not is_git_warning_line(line):
                changed_files.add(line)

        # Untracked
        changed_files.update(git('ls-files', '--others', '--exclude-standard').splitlines())

    return sorted(changed_files, key=lambda relative_path: (relative_path, -relative_path.count('/')))


def get_changed_targets(root: Path, *, ref: str, local: bool, verbose: bool) -> list[str]:
    changed_files = get_changed_files(ref=ref, local=local)
    if verbose:
        print('\n'.join(changed_files), file=sys.stderr)

    changed_directories: dict[str, list[str]] = {}
    for changed_file in changed_files:
        directory_name, _, relative_path = changed_file.partition('/')
        if relative_path:
            changed_directories.setdefault(directory_name, []).append(relative_path)

    targets = []
    for directory_name, files in changed_directories.items():
        directory = root / directory_name
        if not ((directory / 'hatch.toml').is_file() and (directory / 'tests').is_dir()):
            continue

        for relative_path in files:
            possible_file = directory / relative_path
            if possible_file.name in NON_TESTABLE_FILES:
                continue
            elif any(fnmatch(str(possible_file), str(directory / pattern)) for pattern in TESTABLE_FILE_PATTERNS):
                targets.append(directory_name)
                break

    return targets


def get_all_targets(root: Path) -> list[str]:
    targets = []
    for entry in root.iterdir():
        if (entry / 'hatch.toml').is_file() and (entry / 'tests').is_dir():
            targets.append(entry.name)

    return targets


def construct_job_matrix(root: Path, targets: list[str]) -> list[dict[str, Any]]:
    targets = sorted(targets, key=lambda d: (DISPLAY_ORDER_OVERRIDE.get(d, len(DISPLAY_ORDER_OVERRIDE)), d))

    overrides = {}
    if (config_file := root / '.ddev' / 'config.toml').is_file():
        overrides.update(tomllib.loads(config_file.read_text(encoding='utf-8')).get('overrides', {}))

    display_overrides = overrides.get('display-name', {})
    ci_overrides = overrides.get('ci', {})

    job_matrix = []
    for target in targets:
        matrix_overrides = ci_overrides.get(target, {})
        if matrix_overrides.get('exclude', False):
            continue

        manifest = read_manifest(root, target)
        platforms = matrix_overrides.get('platforms', [])
        if not platforms:
            if manifest:
                platforms = []
                for classifier_tag in manifest['tile']['classifier_tags']:
                    key, _, value = classifier_tag.partition('::')
                    if key == 'Supported OS':
                        platforms.append(value.lower())

                # Run only on Linux if not exclusive to Windows
                if platforms != ['windows']:
                    platforms = ['linux']
            else:
                platforms = ['linux']

        runners = matrix_overrides.get('runners', {})
        for platform in platforms:
            if platform not in PLATFORM_NAMES:
                raise ValueError(f'Unsupported platform for `{target}`: {platform}')

            config = {
                'platform': platform,
                'runner': runners.get(platform, [PLATFORM_TO_OS[platform]]),
                'target': target,
            }

            if target in display_overrides:
                config['name'] = display_overrides[target]
            elif manifest:
                config['name'] = manifest['assets']['integration']['source_type_name']
            else:
                config['name'] = target

            if len(platforms) > 1:
                config['name'] += f' on {PLATFORM_NAMES[platform]}'

            if matrix_overrides.get('test-py2', False):
                config['py2'] = True

            config['name'] = normalize_job_name(config['name'])
            job_matrix.append(config)

    return job_matrix


def main():
    root = Path.cwd()
    os.chdir(root)

    parser = argparse.ArgumentParser(prog='devenv', allow_abbrev=False)
    parser.add_argument('--ref', default='origin/master')
    parser.add_argument('-a', '--all', action='store_true')
    parser.add_argument('-p', '--pretty', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    targets = (
        get_all_targets(root)
        if args.all
        else get_changed_targets(root, ref=args.ref, local=args.pretty, verbose=args.verbose)
    )
    job_matrix = construct_job_matrix(root, targets)

    total_jobs = len(job_matrix)
    job_matrix[:] = job_matrix[:JOB_LIMIT]

    output = json.dumps(job_matrix, indent=2) if args.pretty else json.dumps(job_matrix, separators=(',', ':'))
    print(output)

    print(f'Output size: {len(output)} / {OUTPUT_LIMIT}', file=sys.stderr)
    print(f'Number of jobs: {total_jobs}', file=sys.stderr)
    if total_jobs > JOB_LIMIT:
        print(f'Jobs ignored to satisfy limit: {total_jobs - JOB_LIMIT}', file=sys.stderr)


if __name__ == '__main__':
    main()

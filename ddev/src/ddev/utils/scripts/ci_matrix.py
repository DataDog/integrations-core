"""
Running this script by itself requires Python 3.11 or later and must not use any external dependencies.

The logic is also imported by ddev to perform the CI validation on 3.8 which works because dependencies exist.
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
from collections import defaultdict, namedtuple
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

# GitHub Actions' `paths-ignore` job filtering option requires that every changed path must match at least one of
# the exclusion patterns, but we want any to cause that condition for the core repository to run all jobs
SKIPPED_PATTERN = re.compile(
    r"""
    datadog_checks_base/datadog_checks/.+
  | datadog_checks_dev/datadog_checks/dev/[^/]+\.py
    """,
    re.VERBOSE,
)
TESTABLE_FILE_PATTERN = re.compile(
    r"""
    assets/configuration/.+
  | tests/.+
  | [^/]+\.py
  | hatch\.toml
  | metadata\.csv
  | pyproject\.toml
  | datadog_checks/[^/]+/data/metrics\.yaml
  | datadog_checks/snmp/data/default_profiles/.+
    """,
    re.VERBOSE,
)
AGENT_REQUIREMENTS_FILE = 'datadog_checks_base/datadog_checks/base/data/agent_requirements.in'
NON_TESTABLE_FILES = {'auto_conf.yaml'}
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

__plat = namedtuple('__plat', ['name', 'image'])
PLATFORMS = {
    # https://github.com/actions/runner-images/blob/main/images/linux/Ubuntu2204-Readme.md
    'linux': __plat('Linux', 'ubuntu-22.04'),
    # https://github.com/actions/runner-images/blob/main/images/win/Windows2022-Readme.md
    'windows': __plat('Windows', 'windows-2022'),
    # https://github.com/actions/runner-images/blob/main/images/macos/macos-12-Readme.md
    'macos': __plat('macOS', 'macos-12'),
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
            _, relative_path = line.split(maxsplit=1)
            changed_files.add(relative_path)

    if local:
        # Tracked
        for line in git('diff', '--name-only', 'HEAD').splitlines():
            if not is_git_warning_line(line):
                changed_files.add(line)

        # Untracked
        changed_files.update(git('ls-files', '--others', '--exclude-standard').splitlines())

    # Sort for nicer display when using the --verbose flag
    return sorted(changed_files, key=lambda path: (path, -path.count('/')))


def get_changed_targets(root: Path, *, ref: str, local: bool, verbose: bool) -> list[str]:
    changed_files = get_changed_files(ref=ref, local=local)
    if verbose:
        print('\n'.join(changed_files), file=sys.stderr)

    if (
        (root / 'datadog_checks_base').is_dir()
        and AGENT_REQUIREMENTS_FILE not in changed_files
        and any(SKIPPED_PATTERN.search(path) for path in changed_files)
    ):
        return []

    changed_directories: defaultdict[str, list[str]] = defaultdict(list)
    for changed_file in changed_files:
        directory_name, _, remaining_path = changed_file.partition('/')
        if remaining_path:
            changed_directories[directory_name].append(remaining_path)

    agent_requirements_file = root / AGENT_REQUIREMENTS_FILE
    targets = []
    for directory_name, files in changed_directories.items():
        directory = root / directory_name
        if not ((directory / 'hatch.toml').is_file() and (directory / 'tests').is_dir()):
            continue

        for remaining_path in files:
            possible_file = directory / remaining_path
            if possible_file.name in NON_TESTABLE_FILES or possible_file == agent_requirements_file:
                continue
            elif TESTABLE_FILE_PATTERN.search(remaining_path):
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
        platform_ids = matrix_overrides.get('platforms', [])
        if not platform_ids:
            if manifest:
                platform_ids = []
                for classifier_tag in manifest['tile']['classifier_tags']:
                    key, _, value = classifier_tag.partition('::')
                    if key == 'Supported OS':
                        platform_ids.append(value.lower())

                # Run only on Linux if not exclusive to Windows
                if platform_ids != ['windows']:
                    platform_ids = ['linux']
            else:
                platform_ids = ['linux']

        runners = matrix_overrides.get('runners', {})
        for platform_id in platform_ids:
            if platform_id not in PLATFORMS:
                raise ValueError(f'Unsupported platform for `{target}`: {platform_id}')

            platform = PLATFORMS[platform_id]
            config = {
                'platform': platform_id,
                'runner': runners.get(platform_id, [platform.image]),
                'target': target,
            }

            if target in display_overrides:
                config['name'] = display_overrides[target]
            elif manifest and 'integration' in manifest.get('assets', {}):
                config['name'] = manifest['assets']['integration']['source_type_name']
            else:
                config['name'] = target

            if len(platform_ids) > 1:
                config['name'] += f' on {platform.name}'

            supported_python_versions = []
            for major_version in ('2', '3'):
                if matrix_overrides.get(f'only-py{major_version}', False):
                    supported_python_versions.append(major_version)

            if supported_python_versions:
                config['python-support'] = ''.join(supported_python_versions)

            config['name'] = normalize_job_name(config['name'])
            job_matrix.append(config)

    return job_matrix


def main():
    root = Path.cwd()
    os.chdir(root)

    parser = argparse.ArgumentParser(prog=__name__, allow_abbrev=False)
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

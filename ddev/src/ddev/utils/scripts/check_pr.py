"""
Running this script by itself must not use any external dependencies.
"""
# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations
from collections import defaultdict

import os
import re
import sys
from typing import Iterator


def changelog_entry_suffix(pr_number: int, pr_url: str) -> str:
    return f' ([#{pr_number}]({pr_url}))'


def requires_changelog(target: str, files: Iterator[str]) -> bool:
    if target == 'ddev':
        source = 'src/ddev/'
    else:
        if target == 'datadog_checks_base':
            directory = 'base'
        elif target == 'datadog_checks_dev':
            directory = 'dev'
        elif target == 'datadog_checks_downloader':
            directory = 'downloader'
        else:
            directory = target.replace('-', '_')

        source = f'datadog_checks/{directory}/'

    return any(f.startswith(source) or f == 'pyproject.toml' for f in files)


def git(*args) -> str:
    import subprocess

    try:
        process = subprocess.run(
            ['git', *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f'{str(e)[:-1]}:\n{e.output}') from None

    return process.stdout


def extract_filenames(git_diff: str) -> Iterator[str]:
    for modification in re.split(r'^diff --git ', git_diff, flags=re.MULTILINE):
        if not modification:
            continue

        # a/file b/file
        # new file mode 100644
        # index 0000000000..089fd64579
        # --- a/file
        # +++ b/file
        metadata, *_ = re.split(r'^@@ ', modification, flags=re.MULTILINE)
        *_, before, after = metadata.strip().splitlines()

        # Binary files /dev/null and b/foo/archive.tar.gz differ
        binary_indicator = 'Binary files '
        if after.startswith(binary_indicator):
            line = after[len(binary_indicator) :].rsplit(maxsplit=1)[0]
            if line.startswith('/dev/null and '):
                filename = line.split(maxsplit=2)[-1][2:]
            elif line.endswith(' and /dev/null'):
                filename = line.split(maxsplit=2)[0][2:]
            else:
                _, _, filename = line.partition(' and b/')

            yield filename
            continue

        # --- a/file
        # +++ /dev/null
        before = before.split(maxsplit=1)[1]
        after = after.split(maxsplit=1)[1]
        filename = before[2:] if after == '/dev/null' else after[2:]
        yield filename



def get_changelog_errors(git_diff: str, pr_number: int) -> list[str]:
    targets: defaultdict[str, list[str]] = defaultdict(list)
    for filename in extract_filenames(git_diff):
        target, _, path = filename.partition('/')
        if path:
            targets[target].append(path)

    fragments_dir = 'changelog.d'
    errors: list[str] = []
    for target, files in sorted(targets.items()):
        if not requires_changelog(target, iter(files)):
            continue
        changelog_entries = [f for f in files if f.startswith(fragments_dir)]
        if not changelog_entries:
            errors.append(
                f'Package "{target}" is missing a changelog entry for the following changes:\n'
                + '\n'.join(f'- {f}' for f in files)
            )
            continue
        for entry_path in changelog_entries:
            entry_parents, entry_fname = os.path.split(entry_path)
            entry_pr_num, _, entry_fname_rest = entry_fname.partition(".")
            if int(entry_pr_num) != pr_number:
                correct_entry_path = os.path.join(entry_parents, f'{pr_number}.{entry_fname_rest}')
                errors.append(f'Please rename changelog entry file "{entry_path}" to "{correct_entry_path}"')

    return errors


def changelog_impl(*, ref: str, diff_file: str, pr_file: str) -> None:
    import json

    on_ci = os.environ.get('GITHUB_ACTIONS') == 'true'
    if on_ci:
        with open(diff_file, encoding='utf-8') as f:
            git_diff = f.read()

        with open(pr_file, 'r', encoding='utf-8') as f:
            pr = json.loads(f.read())['pull_request']

        pr_number = pr['number']
        pr_labels = [label['name'] for label in pr['labels']]
    else:
        git_diff = git('diff', f'{ref}...')
        pr_number = 1
        pr_labels = []

    if 'changelog/no-changelog' in pr_labels:
        print('No changelog entries required (changelog/no-changelog label found)')
        return

    errors = get_changelog_errors(git_diff, pr_number)
    if not errors:
        return
    for message in errors:
        formatted = '%0A'.join(message.splitlines()) if on_ci else message
        print(f'{formatted}\n')
    print('Please run `ddev release changelog new` to add missing changelog entries.')
    sys.exit(1)


def changelog_command(subparsers) -> None:
    parser = subparsers.add_parser('changelog')
    parser.add_argument('--ref', default='origin/master')
    parser.add_argument('--diff-file')
    parser.add_argument('--pr-file')
    parser.set_defaults(func=changelog_impl)


def main():
    import argparse

    parser = argparse.ArgumentParser(prog=__name__, allow_abbrev=False)
    subparsers = parser.add_subparsers()

    changelog_command(subparsers)

    kwargs = vars(parser.parse_args())
    try:
        # We associate a command function with every subcommand parser.
        # This allows us to emulate Click's command group behavior.
        command = kwargs.pop('func')
    except KeyError:
        parser.print_help()
    else:
        command(**kwargs)


if __name__ == '__main__':
    main()

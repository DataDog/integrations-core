# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from subprocess import CompletedProcess
from textwrap import dedent as _dedent

import pytest


def dedent(text):
    return _dedent(text[1:])


def remove_trailing_spaces(text):
    return ''.join(f'{line.rstrip()}\n' for line in text.splitlines(True))


def error(exception_class, message='', **kwargs):
    if message:
        kwargs['match'] = f'^{re.escape(message)}$'

    return pytest.raises(exception_class, **kwargs)


def changed_file_processes(files: list[str]):
    # This returns the subprocess calls behind `IntegrationRegistry.changed_paths` for tests that
    # have to mock them: a merge base, a diff and an untracked-file listing for every entry in
    # `DEFAULT_COMPARISONS`. The files are reported against the first comparison, which leaves the
    # working tree clean for the second.
    merge_base = CompletedProcess([], 0, stdout='0000000000000000000000000000000000000000\n')
    return [
        merge_base,
        CompletedProcess([], 0, stdout='\n'.join(f'M\t{f}' for f in files)),
        CompletedProcess([], 0, stdout=''),
        merge_base,
        CompletedProcess([], 0, stdout=''),
        CompletedProcess([], 0, stdout=''),
    ]


def write_file(folder, file, content):
    (folder / file).parent.mkdir(exist_ok=True, parents=True)
    file_path = folder / file
    file_path.write_text(content)

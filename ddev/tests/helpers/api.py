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
    # This returns subprocess calls used in `ddev.utils.git.GitManager.get_changed_files`
    # for tests that have to mock subprocess calls
    return [
        CompletedProcess([], 0, stdout='\n'.join(f'M {f}' for f in files)),
        CompletedProcess([], 0, stdout=''),
        CompletedProcess([], 0, stdout=''),
    ]

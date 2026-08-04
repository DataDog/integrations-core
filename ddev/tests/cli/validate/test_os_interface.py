# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the OS interface erosion guard.

Without this validation, a new PR can reintroduce a raw `open()`/`subprocess`
call, or reach for the unenforcing module-level singleton inside a check class,
and every other test still passes while enforcement silently does nothing there.
"""

from __future__ import annotations

import pytest

from tests.helpers.api import write_file

COMPLIANT = """\
from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        with self.os_interface.open(self.instance['path']) as f:
            f.read()
        self.os_interface.run(['ls'], capture_output=True)
"""

RAW_OPEN = """\
from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        with open(self.instance['path']) as f:
            f.read()
"""

RAW_SUBPROCESS = """\
import subprocess

from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        subprocess.run(['ls'], capture_output=True)
"""

SINGLETON_IN_CHECK_CLASS = """\
from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.os_interface import os_interface


class MyCheck(AgentCheck):
    def check(self, _):
        os_interface.run([self.instance['binary']], capture_output=True)
"""

SINGLETON_WITH_WAIVER = """\
from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.os_interface import os_interface

# SKIP_OS_INTERFACE_VALIDATION: bundled asset, no config-derived path
DATA = os_interface.open('bundled.json')


class MyCheck(AgentCheck):
    pass
"""

RAW_OPEN_WITH_WAIVER = """\
from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        # SKIP_OS_INTERFACE_VALIDATION: reads a fixed, non-config path
        with open('/proc/uptime') as f:
            f.read()
"""


def _write_check(repo_path, name, source):
    write_file(repo_path / name, 'manifest.json', '{}')
    write_file(repo_path / name / 'datadog_checks' / name, '__init__.py', '')
    write_file(repo_path / name / 'datadog_checks' / name, 'check.py', source)


@pytest.fixture
def repo_with(fake_repo):
    def _make(name, source):
        _write_check(fake_repo.path, name, source)
        return fake_repo

    return _make


def test_compliant_check_passes(repo_with, ddev):
    repo_with('good', COMPLIANT)
    result = ddev('validate', 'os-interface', 'good')
    assert result.exit_code == 0, result.output


def test_raw_open_is_flagged(repo_with, ddev):
    repo_with('bad', RAW_OPEN)
    result = ddev('validate', 'os-interface', 'bad')
    assert result.exit_code == 1, result.output
    assert 'open(' in result.output


def test_raw_subprocess_is_flagged(repo_with, ddev):
    repo_with('bad', RAW_SUBPROCESS)
    result = ddev('validate', 'os-interface', 'bad')
    assert result.exit_code == 1, result.output
    assert 'subprocess' in result.output


def test_singleton_inside_check_class_is_flagged(repo_with, ddev):
    repo_with('bad', SINGLETON_IN_CHECK_CLASS)
    result = ddev('validate', 'os-interface', 'bad')
    assert result.exit_code == 1, result.output
    assert 'os_interface' in result.output
    assert 'self.os_interface' in result.output


def test_singleton_outside_check_class_is_allowed_with_waiver(repo_with, ddev):
    repo_with('ok', SINGLETON_WITH_WAIVER)
    result = ddev('validate', 'os-interface', 'ok')
    assert result.exit_code == 0, result.output


def test_raw_open_with_waiver_is_allowed(repo_with, ddev):
    repo_with('ok', RAW_OPEN_WITH_WAIVER)
    result = ddev('validate', 'os-interface', 'ok')
    assert result.exit_code == 0, result.output


def test_config_models_are_ignored(fake_repo, ddev):
    write_file(fake_repo.path / 'gen', 'manifest.json', '{}')
    write_file(fake_repo.path / 'gen' / 'datadog_checks' / 'gen', '__init__.py', '')
    write_file(
        fake_repo.path / 'gen' / 'datadog_checks' / 'gen' / 'config_models',
        'instance.py',
        "with open('x') as f:\n    pass\n",
    )
    result = ddev('validate', 'os-interface', 'gen')
    assert result.exit_code == 0, result.output


def test_excluded_integration_is_skipped(repo_with, fake_repo, ddev):
    repo_with('bad', RAW_OPEN)
    write_file(
        fake_repo.path / '.ddev',
        'config.toml',
        '[overrides.validate.os-interface]\nexclude = ["bad"]\n',
    )
    result = ddev('validate', 'os-interface', 'bad')
    assert result.exit_code == 0, result.output


METHOD_NAMED_OPEN = """\
from datadog_checks.base import AgentCheck


class FileDescriptor:
    def open(self, dir):
        return self.fd

    async def open_async(self):
        return None


class MyCheck(AgentCheck):
    def check(self, _):
        with self.os_interface.open('x') as f:
            f.read()
"""

STRING_AND_DOCSTRING_MENTIONS = '''\
from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    """Historically this used open() and subprocess.run() directly."""

    MESSAGE = "call open( to read"

    def check(self, _):
        self.os_interface.run(['ls'])
'''


def test_method_definition_named_open_is_not_flagged(repo_with, ddev):
    # `def open(...)` is a definition, not a call into the stdlib.
    repo_with('ok', METHOD_NAMED_OPEN)
    result = ddev('validate', 'os-interface', 'ok')
    assert result.exit_code == 0, result.output


def test_docstrings_and_string_literals_are_not_flagged(repo_with, ddev):
    repo_with('ok', STRING_AND_DOCSTRING_MENTIONS)
    result = ddev('validate', 'os-interface', 'ok')
    assert result.exit_code == 0, result.output


MULTILINE_WAIVER = """\
import os

from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        # SKIP_OS_INTERFACE_VALIDATION: fixed literal probe with no config input,
        # and it needs a shell for the redirect. The config-derived path below
        # does go through the interface.
        os.system('setsid sudo -l < /dev/null')
"""

WAIVER_SEPARATED_BY_BLANK_LINE = """\
import os

from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        # SKIP_OS_INTERFACE_VALIDATION: too far away to apply

        os.system('rm -rf /')
"""


def test_multiline_waiver_block_applies_to_following_call(repo_with, ddev):
    # A justification often needs more than one line; the whole contiguous
    # comment block above the call counts.
    repo_with('ok', MULTILINE_WAIVER)
    result = ddev('validate', 'os-interface', 'ok')
    assert result.exit_code == 0, result.output


def test_waiver_separated_by_blank_line_does_not_apply(repo_with, ddev):
    # The waiver must be attached to the call, not merely nearby.
    repo_with('bad', WAIVER_SEPARATED_BY_BLANK_LINE)
    result = ddev('validate', 'os-interface', 'bad')
    assert result.exit_code == 1, result.output


FROM_IMPORT_EVASION = """\
from os import scandir
from os.path import exists

from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        if exists(self.instance['path']):
            for entry in scandir(self.instance['path']):
                print(entry)
"""

ALIASED_IMPORT_EVASION = """\
from subprocess import run as run_cmd

from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        run_cmd([self.instance['binary']])
"""

UNRELATED_FROM_IMPORT = """\
from os import environ
from os.path import basename, join

from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        return join(basename(environ['HOME']), 'x')
"""


def test_from_imported_functions_are_flagged(repo_with, ddev):
    # `from os import scandir` evades dotted-name matching.
    repo_with('bad', FROM_IMPORT_EVASION)
    result = ddev('validate', 'os-interface', 'bad')
    assert result.exit_code == 1, result.output
    assert 'scandir' in result.output
    assert 'exists' in result.output


def test_aliased_imports_are_flagged(repo_with, ddev):
    repo_with('bad', ALIASED_IMPORT_EVASION)
    result = ddev('validate', 'os-interface', 'bad')
    assert result.exit_code == 1, result.output
    assert 'run' in result.output


def test_unrelated_from_imports_are_not_flagged(repo_with, ddev):
    # join/basename/environ do no I/O and must not be reported.
    repo_with('ok', UNRELATED_FROM_IMPORT)
    result = ddev('validate', 'os-interface', 'ok')
    assert result.exit_code == 0, result.output


RAW_OS_OPEN = """\
import os

from datadog_checks.base import AgentCheck


class MyCheck(AgentCheck):
    def check(self, _):
        fd = os.open(self.instance['path'], os.O_RDONLY)
        os.close(fd)
"""


def test_raw_os_open_is_flagged(repo_with, ddev):
    # The interface exposes os_open; the dotted form must be caught too, not
    # only the `from os import open` form.
    repo_with('bad', RAW_OS_OPEN)
    result = ddev('validate', 'os-interface', 'bad')
    assert result.exit_code == 1, result.output
    assert 'os.open' in result.output

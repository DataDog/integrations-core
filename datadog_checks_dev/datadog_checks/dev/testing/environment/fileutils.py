# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from contextlib import contextmanager
from tempfile import mkdtemp

from datadog_checks.dev.fileutils import remove_path
from datadog_checks.dev.testing.environment.structures import EnvVars
from datadog_checks.dev.testing.fileutils import resolve_path
from datadog_checks.dev.testing.utils import mock_context_manager


@contextmanager
def chdir(d, cwd=None, env_vars=None):
    origin = cwd or os.getcwd()
    os.chdir(d)
    env_vars = EnvVars(env_vars) if env_vars else mock_context_manager()

    try:
        with env_vars:
            yield
    finally:
        os.chdir(origin)


@contextmanager
def temp_chdir(cwd=None, env_vars=None):
    with temp_dir() as d:
        with chdir(d, cwd=cwd, env_vars=env_vars):
            yield d


@contextmanager
def temp_dir():
    # TODO: On Python 3.5+ just use `with TemporaryDirectory() as d:`.
    d = mkdtemp()

    try:
        d = resolve_path(d)
        yield d
    finally:
        remove_path(d)

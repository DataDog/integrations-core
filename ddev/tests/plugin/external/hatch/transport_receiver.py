# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import locale
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption('--probe-token', action='append', default=[])


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[dict]:
    yield {}


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    result = {
        'python': sys.version.split()[0],
        'pytest': pytest.__version__,
        'encoding': locale.getpreferredencoding(False),
        'utf8_mode': sys.flags.utf8_mode,
        'executable': sys.executable,
        'tokens': config.getoption('probe_token'),
        'paths': config.args,
        'rootdir': str(config.rootpath),
        'config': str(config.inipath),
        'marker': config.option.markexpr,
        'keyword': config.option.keyword,
        'selected': [item.nodeid for item in session.items],
        'status': int(exitstatus),
        'plugins': [name for name, plugin in config.pluginmanager.list_name_plugin() if plugin is not None],
    }
    Path(os.environ['TRANSPORT_RESULT']).write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')

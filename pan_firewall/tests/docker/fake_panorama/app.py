# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Fake Panorama: keygen and `show devices connected`, answered with the synthetic device list."""

import os

from tests.common import FIXTURES
from tests.docker.panos_server import create_app, serve
from tests.fixture_map import PANORAMA_OP_FIXTURES


def op_fixture(cmd):
    relative = PANORAMA_OP_FIXTURES.get(cmd)
    return FIXTURES / relative if relative else None


app = create_app(
    os.environ['PANORAMA_USERNAME'],
    os.environ['PANORAMA_PASSWORD'],
    op_fixture=op_fixture,
    log_fixtures=lambda _data: None,
    report_fixtures=lambda _data: None,
)

if __name__ == '__main__':
    serve(app)

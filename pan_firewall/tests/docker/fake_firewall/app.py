# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Fake PAN-OS firewall answering from one fixture set (`FIREWALL_SET`: `fw-a` or `fw-b`)."""

import os

from tests.docker.panos_server import create_app, serve
from tests.fixture_map import find_op_fixture, report_job_fixture

FIREWALL_SET = os.environ['FIREWALL_SET']


def op_fixture(cmd):
    path = find_op_fixture(cmd, FIREWALL_SET)
    return path.read_bytes() if path else None


app = create_app(
    os.environ['PANOS_USERNAME'],
    os.environ['PANOS_PASSWORD'],
    op_fixture=op_fixture,
    report_fixtures=lambda data: report_job_fixture(data, FIREWALL_SET),
)

if __name__ == '__main__':
    serve(app)

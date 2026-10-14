# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Fake PAN-OS firewall answering from one fixture set (`FIREWALL_SET`: `fw-a` or `fw-b`)."""

import os
import re

from tests.docker.panos_server import create_app, serve
from tests.fixture_map import find_log_fixture, find_op_fixture, find_report_fixture

FIREWALL_SET = os.environ['FIREWALL_SET']


def op_fixture(cmd):
    path = find_op_fixture(cmd, FIREWALL_SET)
    return path.read_bytes() if path else None


def log_fixtures(data):
    skip = int(data.get('skip', '0'))
    return find_log_fixture(data.get('dir', ''), data.get('query'), skip, FIREWALL_SET)


def report_fixtures(data):
    match = re.search(r'<aggregate-by><member>([^<]+)</member>', data.get('cmd', ''))
    return find_report_fixture(match.group(1), FIREWALL_SET) if match else None


app = create_app(
    os.environ['PANOS_USERNAME'],
    os.environ['PANOS_PASSWORD'],
    op_fixture=op_fixture,
    log_fixtures=log_fixtures,
    report_fixtures=report_fixtures,
)

if __name__ == '__main__':
    serve(app)

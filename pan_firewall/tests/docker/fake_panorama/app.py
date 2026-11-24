# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Fake Panorama: keygen and `show devices connected`, answered with the synthetic device list.

The list reports fw-a and fw-b at the fake firewalls' addresses (`FW_A_IP`, `FW_B_IP`), which the check then polls.
"""

import os

from tests.docker.panos_server import create_app, serve
from tests.fixture_map import panorama_op_answer

FIREWALL_IPS = {'fw-a': os.environ['FW_A_IP'], 'fw-b': os.environ['FW_B_IP']}


def op_fixture(cmd):
    return panorama_op_answer(cmd, FIREWALL_IPS)


app = create_app(
    os.environ['PANORAMA_USERNAME'],
    os.environ['PANORAMA_PASSWORD'],
    op_fixture=op_fixture,
    report_fixtures=lambda _data: None,
)

if __name__ == '__main__':
    serve(app)

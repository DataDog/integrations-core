# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .common import HERE, DEFAULT_UNIT_ID, DEFAULT_UNIT_STATE


def mock_systemd_output(fname):
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return f.read(), '', ''


class MockPart(object):
    def __init__(
        self,
        unit_id=DEFAULT_UNIT_ID,
        unit_state=DEFAULT_UNIT_STATE
    ):
        self.unit_id = unit_id
        self.unit_state = unit_state


class MockSystemdMetrics(object):
    units_active = 34
    units_inactive = 45

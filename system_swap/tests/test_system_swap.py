# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import mock
import logging

from datadog_checks.system_swap import SystemSwap

log = logging.getLogger(__file__)


class _PSUtilSwapStatsMock(object):
    def __init__(self, sin, sout):
        self.sin = sin
        self.sout = sout


ORIG_SWAP_IN = float(115332743168)
ORIG_SWAP_OUT = float(22920884224)

SWAP_IN_INCR = 2
SWAP_OUT_INCR = 4

MOCK_PSUTIL_SWAP_STATS = [
    _PSUtilSwapStatsMock(ORIG_SWAP_IN, ORIG_SWAP_OUT),
    _PSUtilSwapStatsMock(ORIG_SWAP_IN + SWAP_IN_INCR, ORIG_SWAP_OUT + SWAP_OUT_INCR),
]


@pytest.fixture
def check():
    return SystemSwap('system_swap', {}, {})


@pytest.fixture
def mock_psutil():
    with mock.patch('psutil.swap_memory', side_effect=MOCK_PSUTIL_SWAP_STATS):
        yield


def test_system_swap(check, mock_psutil, aggregator):

    tags = ["optional:tags"]

    check.check({
        "tags": tags
    })

    aggregator.assert_metric('system.swap.swapped_in', value=ORIG_SWAP_IN, count=1, tags=tags)
    aggregator.assert_metric('system.swap.swapped_out', value=ORIG_SWAP_OUT, count=1, tags=tags)

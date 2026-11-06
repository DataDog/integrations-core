# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pymqi
import pytest

from datadog_checks.ibm_mq.metrics import depth_percent

pytestmark = pytest.mark.unit


def test_depth_percent():
    queue_info = {
        pymqi.CMQC.MQIA_CURRENT_Q_DEPTH: 5,
        pymqi.CMQC.MQIA_MAX_Q_DEPTH: 10,
    }

    assert depth_percent(queue_info) == 50


def test_depth_percent_missing_fields():
    assert depth_percent({}) is None


def test_depth_percent_max_depth_zero():
    # Some queues (e.g. IBM MQ Managed File Transfer control queues) can be
    # reported with a max depth of 0, which must not raise a ZeroDivisionError.
    queue_info = {
        pymqi.CMQC.MQIA_CURRENT_Q_DEPTH: 0,
        pymqi.CMQC.MQIA_MAX_Q_DEPTH: 0,
    }

    assert depth_percent(queue_info) is None

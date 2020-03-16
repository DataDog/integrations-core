# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import FLUENTD_VERSION

requires_1_9 = pytest.mark.skipif(
    FLUENTD_VERSION is None or float(FLUENTD_VERSION) == '1.9',
    reason='This test is for 1.9 only (make sure FLUENTD_VERSION is set)',
)


requires_0_12_23 = pytest.mark.skipif(
    FLUENTD_VERSION is None or float(FLUENTD_VERSION) == '0.12.23',
    reason='This test is for 0.12.23 only (make sure FLUENTD_VERSION is set)',
)
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from packaging import version

from .common import FLUENTD_VERSION

requires_above_1_8 = pytest.mark.skipif(
    FLUENTD_VERSION is None or version.parse(FLUENTD_VERSION) < version.parse('1.8.0'),
    reason='This test is for versions above 1.8 only (make sure FLUENTD_VERSION is set)',
)


requires_below_1_8 = pytest.mark.skipif(
    FLUENTD_VERSION is None or version.parse(FLUENTD_VERSION) >= version.parse('1.8.0'),
    reason='This test is for versions below 1.8 only (make sure FLUENTD_VERSION is set)',
)

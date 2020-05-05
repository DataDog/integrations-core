# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from tests import common
from tests.utils import requires_windows


@pytest.mark.integration
@requires_windows
def test_basic_check(aggregator, check):
    check.check(common.INSTANCE, rate=True)

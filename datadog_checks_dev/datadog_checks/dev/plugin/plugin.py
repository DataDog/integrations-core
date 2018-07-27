# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

try:
    from datadog_checks.stubs import aggregator as __aggregator

    @pytest.fixture
    def aggregator():
        __aggregator.reset()
        return __aggregator

except ImportError:
    @pytest.fixture
    def aggregator():
        raise ImportError('datadog-checks-base is not installed!')

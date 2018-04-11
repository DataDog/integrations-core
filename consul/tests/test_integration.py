# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

@pytest.mark.integration
def test_check(aggregator, spin_up_consul):
    assert True

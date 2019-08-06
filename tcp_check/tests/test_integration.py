# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import common
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.usefixture("dd_environment")
def test_check(aggregator, check, instance):
    check.check(instance)
    common._test_check(aggregator)

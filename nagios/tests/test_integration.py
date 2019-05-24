# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
import pytest

from . import common
import logging

LOGGER = logging.getLogger(__name__)

@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check, instance):
    LOGGER.warning("This test is not doing anything, check README")
    # To do: add shared volume in docker to be able to locally read relevant files
    assert True

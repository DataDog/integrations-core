# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.marklogic import MarklogicCheck

from .common import INSTANCE
from .metrics import GLOBAL_METRICS, STORAGE_HOST_METRICS, STORAGE_FOREST_METRICS


def test_resources_to_monitor():
    instance = INSTANCE.copy()
    instance['resource_filters'] = [
        {
            'resource': 'database',
            'name': 'Documents',
        }
    ]
    check = MarklogicCheck('marklogic', {}, [instance])

    print(check.get_resources_to_monitor())

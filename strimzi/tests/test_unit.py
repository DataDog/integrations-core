# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import HERE, STRIMZI_VERSION

pytestmark = pytest.mark.unit


def test_check(dd_run_check, aggregator, check, instance, mock_http_response):
    mock_http_response(os.path.join(HERE, 'fixtures', STRIMZI_VERSION, 'metrics.txt'))
    dd_run_check(check(instance))

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.directory import DirectoryCheck

from . import common

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator):
    config = common.get_config_stubs(".")[0]
    check = DirectoryCheck(common.CHECK_NAME, {}, [config])
    check.check(config)
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

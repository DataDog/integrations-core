# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import HEALTH_ENDPOINT, METRIC_ENDPOINT

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test(aggregator, dd_run_check, get_check, instance):
    check = get_check(instance)
    dd_run_check(check)

    custom_tags = instance['tags']

    health_tag = f'endpoint:{HEALTH_ENDPOINT}'
    aggregator.assert_service_check('boundary.controller.health', ServiceCheck.OK, tags=[health_tag, *custom_tags])

    metric_tag = f'endpoint:{METRIC_ENDPOINT}'
    aggregator.assert_service_check('boundary.openmetrics.health', ServiceCheck.OK, tags=[metric_tag, *custom_tags])

    metadata_metrics = get_metadata_metrics()
    for metric in metadata_metrics:
        aggregator.assert_metric(metric)

        aggregator.assert_metric_has_tag(metric, metric_tag)
        for tag in custom_tags:
            aggregator.assert_metric_has_tag(metric, tag)

    aggregator.assert_metrics_using_metadata(metadata_metrics, check_submission_type=True)
    aggregator.assert_all_metrics_covered()

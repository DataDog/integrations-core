# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import skip_windows_ci

pytestmark = [skip_windows_ci, pytest.mark.e2e]


def test(dd_agent_check, instance, global_tags):
    aggregator = dd_agent_check(instance, rate=True)

    for subscription_type, num_messages in (('resource_statistics', 1), ('message_flows', 2)):
        tags = [f'subscription:{subscription_type}', *global_tags]
        aggregator.assert_service_check('ibm_ace.mq.subscription', ServiceCheck.OK, tags=tags)
        aggregator.assert_metric('ibm_ace.messages.current', num_messages, tags=tags)

    metadata_metrics = get_metadata_metrics()
    for metric in metadata_metrics:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(metadata_metrics, check_metric_type=False)

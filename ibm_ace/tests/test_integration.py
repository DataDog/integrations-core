# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import skip_windows_ci

pytestmark = [skip_windows_ci, pytest.mark.integration]


@pytest.mark.usefixtures('dd_environment')
def test(dd_run_check, aggregator, instance, global_tags):
    from datadog_checks.ibm_ace import IbmAceCheck

    check = IbmAceCheck('ibm_ace', {}, [instance])
    dd_run_check(check)

    for subscription_type, num_messages in (('resource_statistics', 1), ('message_flows', 2)):
        tags = [f'subscription:{subscription_type}', *global_tags]
        aggregator.assert_service_check('ibm_ace.mq.subscription', ServiceCheck.OK, tags=tags)
        aggregator.assert_metric('ibm_ace.messages.current', num_messages, tags=tags)

    metadata_metrics = get_metadata_metrics()
    for metric in metadata_metrics:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(metadata_metrics, check_metric_type=False)


@pytest.mark.usefixtures('dd_environment')
def test_without_extra_tags(dd_run_check, aggregator, instance):
    instance.pop('tags')

    tags = [f'mq_server:{instance["mq_server"]}', f'mq_port:{instance["mq_port"]}']

    from datadog_checks.ibm_ace import IbmAceCheck

    check = IbmAceCheck('ibm_ace', {}, [instance])
    dd_run_check(check)

    for subscription_type, num_messages in (('resource_statistics', 1), ('message_flows', 2)):
        local_tags = [f'subscription:{subscription_type}', *tags]
        aggregator.assert_service_check('ibm_ace.mq.subscription', ServiceCheck.OK, tags=local_tags)
        aggregator.assert_metric('ibm_ace.messages.current', num_messages, tags=local_tags)

    metadata_metrics = get_metadata_metrics()
    for metric in metadata_metrics:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(metadata_metrics, check_metric_type=False)


def test_critical_service_check(dd_agent_check, instance, global_tags):
    try:
        aggregator = dd_agent_check(instance)
        for subscription_type in ('resource_statistics', 'message_flows'):
            tags = [f'subscription:{subscription_type}', *global_tags]
            aggregator.assert_service_check('ibm_ace.mq.subscription', ServiceCheck.CRITICAL, tags=tags)
    finally:
        subprocess.check_call(['docker', 'start', 'ibm-ace-mq'])

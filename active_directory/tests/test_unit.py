# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.active_directory import ActiveDirectoryCheck
from datadog_checks.active_directory.metrics import DEFAULT_COUNTERS, METRICS_CONFIG
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import PERFORMANCE_OBJECTS


def test(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    mock_performance_objects(PERFORMANCE_OBJECTS)
    check = ActiveDirectoryCheck('active_directory', {}, [{'host': dd_default_hostname}])
    check.hostname = dd_default_hostname
    dd_run_check(check)

    global_tags = ['server:{}'.format(dd_default_hostname)]
    aggregator.assert_service_check('active_directory.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)

    for counter_data in DEFAULT_COUNTERS:
        aggregator.assert_metric(counter_data[3], 9000, count=1, tags=global_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_all_metrics_config(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    """Test that all metrics defined in METRICS_CONFIG are properly collected."""
    mock_performance_objects(PERFORMANCE_OBJECTS)
    check = ActiveDirectoryCheck('active_directory', {}, [{'host': dd_default_hostname}])
    check.hostname = dd_default_hostname
    dd_run_check(check)

    global_tags = ['server:{}'.format(dd_default_hostname)]
    
    # Verify all configured metrics are collected
    for object_name, object_config in METRICS_CONFIG.items():
        metric_prefix = object_config['name']
        for counter_mapping in object_config['counters']:
            for counter_name, metric_config in counter_mapping.items():
                if isinstance(metric_config, dict):
                    metric_suffix = metric_config.get('name') or metric_config.get('metric_name')
                else:
                    metric_suffix = metric_config
                
                metric_name = f'active_directory.{metric_prefix}.{metric_suffix}'
                
                # All metrics should be collected with value 9000 from mock
                if object_name == 'NTDS':
                    aggregator.assert_metric(metric_name, 9000, count=1, tags=global_tags)
                else:
                    # Netlogon and Security metrics should have instance tag
                    instance_tags = global_tags + ['instance:_Total']
                    aggregator.assert_metric(metric_name, 9000, count=1, tags=instance_tags)

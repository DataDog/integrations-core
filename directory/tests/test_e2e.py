# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check):
    instance = common.get_config_stubs(".")[0]
    instance['collect_folder_stats'] = True
    aggregator = dd_agent_check(instance, rate=True)
    for metric in common.DIR_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)
    for metric in common.FOLDER_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS + ['folder_name:/usr'])
    for metric in common.FILE_METRICS:
        for submetric in ['avg', 'max', 'count', 'median', '95percentile']:
            aggregator.assert_metric('{}.{}'.format(metric, submetric), tags=common.EXPECTED_TAGS)
    aggregator.assert_all_metrics_covered()
    exclude = [
        'system.disk.directory.file.bytes.95percentile',
        'system.disk.directory.file.bytes.avg',
        'system.disk.directory.file.bytes.count',
        'system.disk.directory.file.bytes.max',
        'system.disk.directory.file.bytes.median',
        'system.disk.directory.file.created_sec_ago.95percentile',
        'system.disk.directory.file.created_sec_ago.avg',
        'system.disk.directory.file.created_sec_ago.count',
        'system.disk.directory.file.created_sec_ago.max',
        'system.disk.directory.file.created_sec_ago.median',
        'system.disk.directory.file.modified_sec_ago.95percentile',
        'system.disk.directory.file.modified_sec_ago.avg',
        'system.disk.directory.file.modified_sec_ago.count',
        'system.disk.directory.file.modified_sec_ago.max',
        'system.disk.directory.file.modified_sec_ago.median',
    ]
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=exclude)

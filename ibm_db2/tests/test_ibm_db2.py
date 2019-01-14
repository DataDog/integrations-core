# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.ibm_db2 import IbmDb2Check
from . import metrics

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures('dd_environment')
def test_bad_config(aggregator, instance):
    instance['port'] = '60000'
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check(instance)

    aggregator.assert_service_check(check.SERVICE_CHECK_CONNECT, check.CRITICAL)


@pytest.mark.usefixtures('dd_environment')
def test_standard(aggregator, instance):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check(instance)

    aggregator.assert_service_check(check.SERVICE_CHECK_CONNECT, check.OK)

    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
def test_buffer_pool_tags(aggregator, instance):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check(instance)

    for metric in metrics.BUFFERPOOL:
        aggregator.assert_metric_has_tag_prefix(metric, 'bufferpool:')


@pytest.mark.usefixtures('dd_environment')
def test_table_space_tags(aggregator, instance):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check(instance)

    for metric in metrics.TABLESPACE:
        aggregator.assert_metric_has_tag_prefix(metric, 'tablespace:')


@pytest.mark.usefixtures('dd_environment')
def test_table_space_state_change(aggregator, instance):
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._table_space_states['USERSPACE1'] = 'test'
    check.check(instance)

    aggregator.assert_event('State of `USERSPACE1` changed from `test` to `NORMAL`.')


@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, instance):
    instance['custom_queries'] = [{
        'metric_prefix': 'ibm_db2',
        'tags': ['test:ibm_db2'],
        'query': 'SELECT files_closed, tbsp_name FROM TABLE(MON_GET_TABLESPACE(NULL, -1))',
        'columns': [
            {'name': 'tablespace.files_closed', 'type': 'monotonic_count'},
            {'name': 'tablespace', 'type': 'tag'},
        ],
    }]

    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.check(instance)

    # There is also `SYSTOOLSPACE` but it seems that takes some time to come up
    table_spaces = ['USERSPACE1', 'TEMPSPACE1', 'SYSCATSPACE']

    for table_space in table_spaces:
        aggregator.assert_metric(
            'ibm_db2.tablespace.files_closed',
            metric_type=3,
            tags=['db:datadog', 'foo:bar', 'test:ibm_db2', 'tablespace:{}'.format(table_space)]
        )


@pytest.mark.usefixtures('dd_environment')
def test_custom_queries_init_config(aggregator, instance):
    init_config = {
        'custom_queries': [{
            'metric_prefix': 'ibm_db2',
            'tags': ['test:ibm_db2'],
            'query': 'SELECT files_closed, tbsp_name FROM TABLE(MON_GET_TABLESPACE(NULL, -1))',
            'columns': [
                {'name': 'tablespace.files_closed', 'type': 'monotonic_count'},
                {'name': 'tablespace', 'type': 'tag'},
            ],
        }]
    }

    check = IbmDb2Check('ibm_db2', init_config, [instance])
    check.check(instance)

    # There is also `SYSTOOLSPACE` but it seems that takes some time to come up
    table_spaces = ['USERSPACE1', 'TEMPSPACE1', 'SYSCATSPACE']

    for table_space in table_spaces:
        aggregator.assert_metric(
            'ibm_db2.tablespace.files_closed',
            metric_type=3,
            tags=['db:datadog', 'foo:bar', 'test:ibm_db2', 'tablespace:{}'.format(table_space)]
        )

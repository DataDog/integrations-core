# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from contextlib import nullcontext as does_not_raise

import pytest

from datadog_checks.cloudera import ClouderaCheck


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize(
    'instance, dd_run_check_count, expected_exception, expected_service_checks, expected_events',
    [
        (
            {'api_url': 'http://bad_host:8080/api/v48/'},
            1,
            pytest.raises(
                Exception,
                match='HTTPConnectionPool',
            ),
            [
                {'status': ClouderaCheck.CRITICAL, 'message': None, 'tags': ['api_url:http://bad_host:8080/api/v48/']},
            ],
            [],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/'},
            1,
            does_not_raise(),
            [{'status': ClouderaCheck.OK, 'message': None, 'tags': ['api_url:http://localhost:8080/api/v48/']}],
            [
                {
                    'count': 1,
                    'msg_text': "ExecutionException running extraction tasks for service 'cod--qfdcinkqrzw::yarn'.",
                }
            ],
        ),
    ],
    ids=['bad url', 'good url'],
    indirect=[],
)
def test_api_urls(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    dd_run_check_count,
    expected_exception,
    expected_service_checks,
    expected_events,
):
    with expected_exception:
        check = cloudera_check(instance)
        for _ in range(dd_run_check_count):
            dd_run_check(check)
        for expected_service_check in expected_service_checks:
            aggregator.assert_service_check(
                'cloudera.can_connect',
                status=expected_service_check['status'],
                message=expected_service_check['message'],
                tags=expected_service_check['tags'],
            )
        for expected_event in expected_events:
            aggregator.assert_event(expected_event.get('msg_text'), count=expected_event.get('count'))


#
# @pytest.mark.usefixtures('dd_environment')
# @pytest.mark.integration
# def test_given_api_v48_endpoint_when_check_runs_then_service_check_ok_and_metrics(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
# ):
#     # Given
#     check = cloudera_check(instance)
#     # When
#     dd_run_check(check)
#     # Then
#     for category, metrics in METRICS.items():
#         for metric in metrics:
#             aggregator.assert_metric(f'cloudera.{category}.{metric}', at_least=1)
#             aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_cluster")
#             aggregator.assert_metric_has_tag(f'cloudera.{category}.{metric}', "test1")
#
#             # Only non-cluster metrics have rack_id tags
#             if category != 'cluster':
#                 aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_rack_id")
#
#             # Host metrics should not have a cloudera_host tag, since cloudera_hostname already exists
#             if category == "host":
#                 aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_host:", count=0)
#                 aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', "cloudera_hostname")
#
#     # All timeseries metrics should have cloudera_{category} tag
#     for category, metrics in TIMESERIES_METRICS.items():
#         for metric in metrics:
#             aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', f"cloudera_{category}")
#
#     aggregator.assert_service_check(
#         'cloudera.can_connect',
#         ClouderaCheck.OK,
#         tags=CAN_CONNECT_TAGS,
#     )
#     aggregator.assert_service_check(
#         'cloudera.cluster.health',
#         ClouderaCheck.OK,
#         tags=CLUSTER_1_HEALTH_TAGS,
#     )
#     aggregator.assert_service_check('cloudera.host.health', ClouderaCheck.OK)
#     aggregator.assert_event(
#         "ExecutionException running extraction tasks for service 'cod--qfdcinkqrzw::yarn'.", count=1
#     )
#     aggregator.assert_all_metrics_covered()
#
#
# @pytest.mark.usefixtures('dd_environment')
# @pytest.mark.integration
# def test_metadata(cloudera_check, instance, datadog_agent, dd_run_check):
#     check = cloudera_check(instance)
#     check.check_id = 'test:123'
#     dd_run_check(check)
#
#     raw_version = '7.2.15'
#     major, minor, patch = raw_version.split('.')
#     version_metadata = {
#         'version.scheme': 'cloudera',
#         'version.major': major,
#         'version.minor': minor,
#         'version.patch': patch,
#     }
#
#     datadog_agent.assert_metadata('test:123', version_metadata)
#
#
# @pytest.mark.usefixtures('dd_environment')
# @pytest.mark.integration
# def test_given_custom_queries_then_retrieve_metrics_no_alias(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
# ):
#     # Given
#     instance['custom_queries'] = [
#         {
#             'query': "SELECT jvm_gc_rate, jvm_free_memory",
#             'tags': ["custom_tag:1"],
#         },
#     ]
#
#     check = cloudera_check(instance)
#     # When
#     dd_run_check(check)
#     # Then
#     # Note: jvm_gc_rate and jvm_free_memory are both of category CMSERVER
#     aggregator.assert_metric(
#         "cloudera.cmserver.jvm_gc_rate", tags=["custom_tag:1", "cloudera_cmserver:cloudera_manager_server"]
#     )
#     aggregator.assert_metric(
#         "cloudera.cmserver.jvm_free_memory", tags=["custom_tag:1", "cloudera_cmserver:cloudera_manager_server"]
#     )
#
#
# @pytest.mark.usefixtures('dd_environment')
# @pytest.mark.integration
# def test_given_custom_queries_then_retrieve_metrics_alias(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
# ):
#     # Given
#     instance['custom_queries'] = [
#         {
#             'query': "SELECT jvm_gc_rate as foo",
#             'tags': ["custom_tag:1"],
#         },
#     ]
#
#     check = cloudera_check(instance)
#     # When
#     dd_run_check(check)
#     # Then
#     aggregator.assert_metric(
#         "cloudera.cmserver.foo", tags=["custom_tag:1", "cloudera_cmserver:cloudera_manager_server"]
#     )
#     aggregator.assert_metric(
#         "cloudera.cmserver.jvm_gc_rate", tags=["custom_tag:1", "cloudera_cmserver:cloudera_manager_server"], count=0
#     )
#
#
# @pytest.mark.usefixtures('dd_environment')
# @pytest.mark.integration
# def test_given_custom_queries_then_retrieve_metrics_last_alias(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
# ):
#     # Given
#     instance['custom_queries'] = [
#         {
#             'query': "SELECT last(jvm_gc_rate) as jvm_gc_rate, last(jvm_free_memory) as jvm_free_memory",
#             'tags': ["custom_tag:1"],
#         },
#     ]
#
#     check = cloudera_check(instance)
#     # When
#     dd_run_check(check)
#     # Then
#     aggregator.assert_metric(
#         "cloudera.cmserver.jvm_gc_rate", tags=["custom_tag:1", "cloudera_cmserver:cloudera_manager_server"]
#     )
#     aggregator.assert_metric(
#         "cloudera.cmserver.jvm_free_memory", tags=["custom_tag:1", "cloudera_cmserver:cloudera_manager_server"]
#     )
#
#
# @pytest.mark.usefixtures('dd_environment')
# @pytest.mark.integration
# def test_given_non_existent_custom_query_then_output_no_metric(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
#     caplog,
# ):
#     # Given
#     instance['custom_queries'] = [
#         {
#             'query': "select fake_foo",  # fake_foo doesn't exist
#             'tags': ["baz"],
#         }
#     ]
#     caplog.clear()
#     caplog.set_level(logging.WARNING)
#
#     check = cloudera_check(instance)
#     # When
#     dd_run_check(check)
#     # Then
#     aggregator.assert_metric("cloudera.fake_foo", tags=["baz"], count=0)
#     # No custom metrics, but rest of check is OK
#     aggregator.assert_service_check(
#         'cloudera.can_connect',
#         ClouderaCheck.OK,
#         tags=CAN_CONNECT_TAGS,
#     )
#
#     assert "Invalid metric 'fake_foo' in 'select fake_foo'" in caplog.text
#
#
# @pytest.mark.usefixtures('dd_environment')
# @pytest.mark.integration
# def test_given_incorrect_formatting_custom_query_then_output_no_metric(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
#     caplog,
# ):
#     # Given
#     instance['custom_queries'] = [
#         {
#             'query': "selectt",
#             'tags': ["baz"],
#         }
#     ]
#     caplog.clear()
#     caplog.set_level(logging.WARNING)
#
#     check = cloudera_check(instance)
#     # When
#     dd_run_check(check)
#     # Then
#     # No custom metrics, but rest of check is OK
#     aggregator.assert_service_check(
#         'cloudera.can_connect',
#         ClouderaCheck.OK,
#         tags=CAN_CONNECT_TAGS,
#     )
#     # Look for error log
#     assert "Invalid syntax: no viable alternative at input 'selectt'." in caplog.text

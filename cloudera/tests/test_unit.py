# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# def test_given_cloudera_check_when_no_events_response_then_no_event_collection(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     instance,
#     cloudera_version_7_0_0,
#     list_one_cluster_good_health_resource,
#     list_hosts_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_one_cluster_good_health_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         side_effect=get_timeseries_resource,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.list_hosts',
#         return_value=list_hosts_resource,
#     ), mock.patch(
#         'cm_client.EventsResourceApi.read_events',
#         side_effect=Exception,
#     ):
#         # Given
#         check = cloudera_check(instance)
#         # When
#         dd_run_check(check)
#         # Then
#         aggregator.assert_service_check(
#             'cloudera.can_connect',
#             AgentCheck.OK,
#             tags=CAN_CONNECT_TAGS,
#         )
#         expected_content = (
#             'Interceptor for {http://yarn.extractor.cdx.cloudera.com/}YarnHistoryClient '
#             'has thrown exception, unwinding now'
#         )
#         # verify that event is not collected, but check still works normally
#         aggregator.assert_event(msg_text=expected_content, count=0)
#
#
# def test_given_custom_queries_then_retrieve_metrics_unit(
#     aggregator,
#     dd_run_check,
#     cloudera_check,
#     list_one_cluster_good_health_resource,
#     cloudera_version_7_0_0,
#     instance,
#     get_custom_timeseries_resource,
# ):
#     with mock.patch(
#         'cm_client.ClouderaManagerResourceApi.get_version',
#         return_value=cloudera_version_7_0_0,
#     ), mock.patch(
#         'cm_client.ClustersResourceApi.read_clusters',
#         return_value=list_one_cluster_good_health_resource,
#     ), mock.patch(
#         'cm_client.TimeSeriesResourceApi.query_time_series',
#         return_value=get_custom_timeseries_resource,
#     ):
#         # Given
#         instance['custom_queries'] = [
#             {'query': "select foo"},  # foo is given category of cluster in common.py
#         ]
#
#         check = cloudera_check(instance)
#         # When
#         dd_run_check(check)
#         # Then
#         aggregator.assert_metric("cloudera.cluster.foo")

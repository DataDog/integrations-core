# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Site health and global network health collectors."""

from __future__ import annotations

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient
from datadog_checks.cisco_catalyst_center.collectors import collect_network_health, collect_site_health

from .common import load_captured, metric_values, with_value
from .conftest import ScriptedHttp


def _check(instance):
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


def _client(instance, payload):
    return CatalystCenterClient(instance, http=ScriptedHttp([payload]))


# -- site health ------------------------------------------------------------------


def test_collect_site_health_emits_device_counts_per_site(aggregator, instance):
    collect_site_health(_check(instance), _client(instance, load_captured('data_site_health_summaries')))

    aggregator.assert_metric('cisco_catalyst_center.site.device.count', at_least=20)


def test_collect_site_health_uses_the_endpoint_page_limit_of_twenty(aggregator, instance):
    # siteHealthSummaries rejects limit=500 with `2005 Value must be in the range 1-20`.
    client = _client(instance, load_captured('data_site_health_summaries'))

    collect_site_health(_check(instance), client)

    assert client.http.requests[0]['params']['limit'] == 20


def test_collect_site_health_derives_site_name_from_the_hierarchy(aggregator, instance):
    # There is no siteName field. The leaf of siteHierarchy is the name.
    collect_site_health(_check(instance), _client(instance, load_captured('data_site_health_summaries')))

    assert metric_values(
        aggregator, 'cisco_catalyst_center.site.device.count', 'site_name:Bhagalpur', 'device_family:access'
    )


def test_collect_site_health_given_colliding_site_names_keeps_them_separate(aggregator, instance):
    # Site names are not unique across the hierarchy, so site_id is the identity tag.
    payload = load_captured('data_site_health_summaries')
    payload = with_value(payload, 'response.1.siteHierarchy', 'Global/Elsewhere/Bhagalpur')

    collect_site_health(_check(instance), _client(instance, payload))

    by_name = metric_values(
        aggregator, 'cisco_catalyst_center.site.device.count', 'site_name:Bhagalpur', 'device_family:access'
    )
    assert len(by_name) == 2, 'two distinct sites share a name and must remain two series'


def test_collect_site_health_tags_client_metrics_by_connection_type(aggregator, instance):
    collect_site_health(_check(instance), _client(instance, load_captured('data_site_health_summaries')))

    aggregator.assert_metric_has_tag('cisco_catalyst_center.site.client.count', 'client_type:wireless')


def test_collect_site_health_emits_issue_counts_by_priority(aggregator, instance):
    collect_site_health(_check(instance), _client(instance, load_captured('data_site_health_summaries')))

    aggregator.assert_metric_has_tag('cisco_catalyst_center.site.issue.count', 'priority:p1')


# -- network health ---------------------------------------------------------------


def test_collect_network_health_reads_the_top_level_score_not_a_time_bucket(aggregator, instance):
    # `response` is a time-bucketed array; latestHealthScore is a top-level sibling. Reading
    # response[0].healthScore picks an arbitrary bucket and looks right whenever they agree.
    payload = with_value(load_captured('intent_network_health'), 'response.0.healthScore', 42)

    collect_network_health(_check(instance), _client(instance, payload))

    assert metric_values(aggregator, 'cisco_catalyst_center.network.health') == [100]


def test_collect_network_health_emits_device_totals(aggregator, instance):
    collect_network_health(_check(instance), _client(instance, load_captured('intent_network_health')))

    assert metric_values(aggregator, 'cisco_catalyst_center.network.device.total.count') == [4]


def test_collect_network_health_reads_the_misspelled_distribution_key(aggregator, instance):
    # `healthDistirubution` is genuinely misspelled in the API.
    collect_network_health(_check(instance), _client(instance, load_captured('intent_network_health')))

    assert metric_values(aggregator, 'cisco_catalyst_center.network.category.health', 'category:Access') == [100]

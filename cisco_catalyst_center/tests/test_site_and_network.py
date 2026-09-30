# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Site health and global network health collectors."""

from __future__ import annotations

from datadog_checks.cisco_catalyst_center.collectors import collect_network_health, collect_site_health

from .common import client_from_payload as _client
from .common import load_captured, metric_values, with_value

# -- site health ------------------------------------------------------------------


def test_collect_site_health_given_the_captured_page_emits_the_expected_series(aggregator, instance, check):
    # One recorded page of 20 sites, and what the collector makes of it. The site name is the one
    # derived value in here: there is no siteName field, so the leaf of siteHierarchy is the name.
    collect_site_health(check, _client(instance, load_captured('data_site_health_summaries')))

    aggregator.assert_metric('cisco_catalyst_center.site.device.count', count=160)
    aggregator.assert_metric('cisco_catalyst_center.site.client.count', count=40)
    aggregator.assert_metric('cisco_catalyst_center.site.issue.count', count=80)
    assert metric_values(
        aggregator, 'cisco_catalyst_center.site.device.count', 'site_name:Bhagalpur', 'device_family:access'
    )
    aggregator.assert_metric_has_tag('cisco_catalyst_center.site.client.count', 'client_type:wireless')
    aggregator.assert_metric_has_tag('cisco_catalyst_center.site.issue.count', 'priority:p1')


def test_collect_site_health_given_colliding_site_names_keeps_them_separate(aggregator, instance, check):
    # Site names are not unique across the hierarchy, so site_id is the identity tag.
    payload = load_captured('data_site_health_summaries')
    payload = with_value(payload, 'response.1.siteHierarchy', 'Global/Elsewhere/Bhagalpur')

    collect_site_health(check, _client(instance, payload))

    by_name = metric_values(
        aggregator, 'cisco_catalyst_center.site.device.count', 'site_name:Bhagalpur', 'device_family:access'
    )
    assert len(by_name) == 2, 'two distinct sites share a name and must remain two series'


# -- network health ---------------------------------------------------------------


def test_collect_network_health_reads_the_top_level_score_not_a_time_bucket(aggregator, instance, check):
    # `response` is a time-bucketed array; latestHealthScore is a top-level sibling. Reading
    # response[0].healthScore picks an arbitrary bucket and looks right whenever they agree.
    payload = with_value(load_captured('intent_network_health'), 'response.0.healthScore', 42)

    collect_network_health(check, _client(instance, payload))

    assert metric_values(aggregator, 'cisco_catalyst_center.network.health') == [100]


def test_collect_network_health_given_the_captured_payload_emits_the_expected_series(aggregator, instance, check):
    # The per-category breakdown hangs off `healthDistirubution`, which is genuinely misspelled
    # in the API -- correcting the spelling here collects nothing.
    collect_network_health(check, _client(instance, load_captured('intent_network_health')))

    assert metric_values(aggregator, 'cisco_catalyst_center.network.device.total.count') == [4]
    assert metric_values(aggregator, 'cisco_catalyst_center.network.category.health', 'category:Access') == [100]

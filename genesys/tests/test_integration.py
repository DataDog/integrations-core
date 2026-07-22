# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Integration-style tests that exercise the full check against realistic
Genesys Cloud Analytics Conversation Detail Query API responses.

There is no self-hostable Genesys dependency, so instead of a Docker Compose
environment these tests replay documented API payloads (see tests/fixtures)
through the real ``PureCloudPlatformClientV2`` SDK deserializer. That gives the
check genuine SDK model objects to walk, so the SDK field contract
(``mediaStatsMinConversationMos`` -> ``media_stats_min_conversation_mos``,
etc.), the pagination loop, cross-page dedupe, threshold math, and metric /
service-check submission are all validated end to end. The tests also assert
that the query the check *sends* matches the documented API contract.

Response shape reference:
https://developer.genesys.cloud/analyticsdatamanagement/analytics/detail/conversation-query
"""

import pytest
from mock import MagicMock, patch

from datadog_checks.genesys_mos import GenesysMosCheck

from .common import read_fixture

pytestmark = pytest.mark.integration

RESPONSE_TYPE = "AnalyticsConversationQueryResponse"
EXPECTED_TAGS = ["region:mypurecloud.com", "team:voice"]


class _FakeRestResponse(object):
    """Minimal stand-in for the SDK's RESTResponse. ``deserialize`` reads the
    raw JSON body from ``.data`` and inspects the ``Content-Type`` header to
    decide whether to JSON-decode it."""

    def __init__(self, data):
        self.data = data

    def getheader(self, name, default=None):
        if name.lower() == "content-type":
            return "application/json"
        return default

    def getheaders(self):
        return {"Content-Type": "application/json"}


def _load_response(api_client, fixture_name):
    """Deserialize a fixture into a real SDK response object."""
    raw = read_fixture(fixture_name)
    return api_client.deserialize(_FakeRestResponse(raw), RESPONSE_TYPE)


def _analytics_api_returning(pages):
    """Build a fake AnalyticsApi that pages through ``pages`` by page_number and
    records every query body it received."""
    api = MagicMock()
    calls = []

    def _query(body):
        calls.append(body)
        index = body.paging.page_number - 1
        return pages[index] if index < len(pages) else pages[-1]

    api.post_analytics_conversations_details_query.side_effect = _query
    api.received_queries = calls
    return api


def _run_check(instance, analytics_api):
    check = GenesysMosCheck("genesys_mos", {}, [instance])
    with patch.object(check, "_authenticate", return_value=analytics_api):
        check.check(None)
    return check


def test_documented_pagination_dedupe_and_metrics(aggregator, instance):
    import PureCloudPlatformClientV2 as genesys

    api_client = genesys.api_client.ApiClient()
    pages = [
        _load_response(api_client, "conversations_page1.json"),
        _load_response(api_client, "conversations_page2.json"),
        _load_response(api_client, "conversations_empty.json"),
    ]
    analytics_api = _analytics_api_returning(pages)

    _run_check(instance, analytics_api)

    # Page 1: 4.42, 4.05 | Page 2: 4.05 (duplicate id), 3.61 -> 3 unique conversations.
    values = [4.42, 4.05, 3.61]
    aggregator.assert_metric("genesys_mos.conversation.count", value=3, tags=EXPECTED_TAGS)
    aggregator.assert_metric("genesys_mos.conversation.mos.avg", value=sum(values) / len(values), tags=EXPECTED_TAGS)
    aggregator.assert_metric("genesys_mos.conversation.mos.min", value=3.61, tags=EXPECTED_TAGS)
    # threshold 4.2 -> 4.05 and 3.61 are at/below.
    aggregator.assert_metric("genesys_mos.conversation.below_threshold.count", value=2, tags=EXPECTED_TAGS)
    aggregator.assert_metric("genesys_mos.can_connect", value=1, tags=EXPECTED_TAGS)
    aggregator.assert_all_metrics_covered()

    # Paged until an empty page was returned (3 requests: page 1, 2, and the empty page 3).
    assert len(analytics_api.received_queries) == 3


def test_query_body_matches_genesys_api_contract(aggregator, instance):
    import PureCloudPlatformClientV2 as genesys

    api_client = genesys.api_client.ApiClient()
    analytics_api = _analytics_api_returning([_load_response(api_client, "conversations_empty.json")])

    _run_check(instance, analytics_api)

    body = analytics_api.received_queries[0]

    # Trailing RFC3339 window "<start>/<end>".
    start, end = body.interval.split("/")
    assert start < end

    # AND filter over the two documented "exists" predicates.
    conversation_filter = body.conversation_filters[0]
    assert conversation_filter.type == "and"
    predicates = {p.dimension: p.operator for p in conversation_filter.predicates}
    assert predicates == {
        "mediaStatsMinConversationMos": "exists",
        "conversationEnd": "exists",
    }

    # Paging starts at page 1 and respects the API's 100-row cap.
    assert body.paging.page_size == 100
    assert body.paging.page_number == 1


def test_conversation_without_mos_is_skipped(aggregator, instance):
    import PureCloudPlatformClientV2 as genesys

    api_client = genesys.api_client.ApiClient()
    pages = [
        _load_response(api_client, "conversations_partial_mos.json"),
        _load_response(api_client, "conversations_empty.json"),
    ]
    analytics_api = _analytics_api_returning(pages)

    _run_check(instance, analytics_api)

    # One conversation carries MOS (4.30); the other has no mediaStatsMinConversationMos
    # and must be skipped rather than counted as a zero.
    aggregator.assert_metric("genesys_mos.conversation.count", value=1, tags=EXPECTED_TAGS)
    aggregator.assert_metric("genesys_mos.conversation.mos.avg", value=4.30, tags=EXPECTED_TAGS)
    aggregator.assert_metric("genesys_mos.conversation.mos.min", value=4.30, tags=EXPECTED_TAGS)
    aggregator.assert_metric("genesys_mos.conversation.below_threshold.count", value=0, tags=EXPECTED_TAGS)
    aggregator.assert_metric("genesys_mos.can_connect", value=1, tags=EXPECTED_TAGS)

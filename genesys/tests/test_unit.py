# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# Authored by Ed Ferron
import re

import pytest
from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.genesys import GenesysMosCheck
from mock import MagicMock, patch

pytestmark = pytest.mark.unit


def _check(instance):
    return GenesysMosCheck("genesys_mos", {}, [instance])


def test_configuration_models_load_from_spec(instance):
    # Exercise the spec-generated config models the way the Agent does before a
    # run (via check_initializations), validating that a well-formed instance
    # maps cleanly onto InstanceConfig/SharedConfig.
    check = _check(instance)
    check.load_configuration_models()

    assert check._config_model_shared is not None
    assert check._config_model_instance is not None
    assert check._config_model_instance.region == "mypurecloud.com"
    assert check._config_model_instance.client_id == "test-client-id"
    assert check._config_model_instance.mos_threshold == 4.2
    assert check._config_model_instance.min_collection_interval == 300
    assert check._config_model_instance.tags == ("team:voice",)


def test_config_requires_region(instance):
    del instance["region"]
    with pytest.raises(ConfigurationError, match="region"):
        _check(instance)


def test_config_requires_credentials(instance):
    del instance["client_secret"]
    with pytest.raises(ConfigurationError, match="client_id"):
        _check(instance)


def test_query_interval_is_rfc3339_range(instance):
    check = _check(instance)
    interval = check._query_interval()
    start, end = interval.split("/")
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$"
    assert re.match(pattern, start)
    assert re.match(pattern, end)
    assert start < end


def test_emits_distribution_gauges_and_can_connect(aggregator, instance):
    check = _check(instance)
    conversations = {"c1": 4.8, "c2": 4.1, "c3": 3.5}

    with (
        patch.object(check, "_authenticate", return_value=MagicMock()),
        patch.object(check, "_collect_conversations", return_value=conversations),
    ):
        check.check(None)

    tags = ["region:mypurecloud.com", "team:voice"]
    aggregator.assert_metric("genesys_mos.conversation.count", value=3, tags=tags)
    aggregator.assert_metric("genesys_mos.conversation.mos.avg", value=(4.8 + 4.1 + 3.5) / 3, tags=tags)
    aggregator.assert_metric("genesys_mos.conversation.mos.min", value=3.5, tags=tags)
    # threshold 4.2 -> 4.1 and 3.5 are at/below
    aggregator.assert_metric("genesys_mos.conversation.below_threshold.count", value=2, tags=tags)
    # Connectivity is reported as a 0/1 gauge, not a service check.
    aggregator.assert_metric("genesys_mos.can_connect", value=1, tags=tags)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_no_conversations_reports_zero(aggregator, instance):
    check = _check(instance)
    with (
        patch.object(check, "_authenticate", return_value=MagicMock()),
        patch.object(check, "_collect_conversations", return_value={}),
    ):
        check.check(None)

    tags = ["region:mypurecloud.com", "team:voice"]
    aggregator.assert_metric("genesys_mos.conversation.count", value=0, tags=tags)
    aggregator.assert_metric("genesys_mos.conversation.below_threshold.count", value=0, tags=tags)
    # No quality gauges when there is no data.
    aggregator.assert_metric("genesys_mos.conversation.mos.avg", count=0)
    aggregator.assert_metric("genesys_mos.conversation.mos.min", count=0)
    aggregator.assert_metric("genesys_mos.can_connect", value=1)


def test_auth_failure_reports_can_connect_zero_and_raises(aggregator, instance):
    check = _check(instance)
    with patch.object(check, "_authenticate", side_effect=RuntimeError("bad secret")):
        with pytest.raises(RuntimeError, match="bad secret"):
            check.check(None)

    aggregator.assert_metric("genesys_mos.can_connect", value=0)
    aggregator.assert_metric("genesys_mos.conversation.count", count=0)


def test_collect_conversations_pages_and_dedupes(instance):
    check = _check(instance)

    def make_conversation(cid, mos):
        conv = MagicMock()
        conv.conversation_id = cid
        conv.media_stats_min_conversation_mos = mos
        return conv

    page1 = MagicMock()
    page1.conversations = [make_conversation("c1", 4.5), make_conversation("c2", 3.9)]
    page2 = MagicMock()
    # c2 repeated across page boundary -> must dedupe
    page2.conversations = [make_conversation("c2", 3.9), make_conversation("c3", 4.9)]
    page3 = MagicMock()
    page3.conversations = None

    analytics_api = MagicMock()
    analytics_api.post_analytics_conversations_details_query.side_effect = [page1, page2, page3]

    # Avoid importing the real Genesys SDK: inject a stub module whose classes
    # are permissive MagicMock factories.
    genesys_stub = MagicMock()
    with patch.dict("sys.modules", {"PureCloudPlatformClientV2": genesys_stub}):
        result = check._collect_conversations(analytics_api, "start/end")

    assert result == {"c1": 4.5, "c2": 3.9, "c3": 4.9}
    assert analytics_api.post_analytics_conversations_details_query.call_count == 3

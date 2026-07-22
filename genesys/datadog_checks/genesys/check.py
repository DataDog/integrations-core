# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# Authored by Ed Ferron
from datetime import datetime, timedelta, timezone

from datadog_checks.base import AgentCheck, ConfigurationError

# MOS (Mean Opinion Score) is reported directly by Genesys Cloud on the
# `mediaStatsMinConversationMos` dimension of the Analytics Conversation Detail
# Query API. It is the minimum MOS observed on a conversation and ranges roughly
# 1.0 (unusable) to ~4.9 (toll quality); it is NOT computed by this check.
MOS_DIMENSION = "mediaStatsMinConversationMos"
CONVERSATION_END_DIMENSION = "conversationEnd"

# Page size cap enforced by the Genesys analytics API.
PAGE_SIZE = 100

DEFAULT_INTERVAL_SECONDS = 300
DEFAULT_LAG_SECONDS = 60
DEFAULT_MOS_THRESHOLD = 4.2


class GenesysMosCheck(AgentCheck):
    __NAMESPACE__ = "genesys_mos"

    CAN_CONNECT_METRIC = "can_connect"

    def __init__(self, name, init_config, instances):
        super(GenesysMosCheck, self).__init__(name, init_config, instances)

        self.region = self.instance.get("region")
        self.client_id = self.instance.get("client_id")
        self.client_secret = self.instance.get("client_secret")
        self.mos_threshold = float(self.instance.get("mos_threshold", DEFAULT_MOS_THRESHOLD))
        self.lag_seconds = int(self.instance.get("collection_lag_seconds", DEFAULT_LAG_SECONDS))
        self.window_seconds = int(self.instance.get("min_collection_interval", DEFAULT_INTERVAL_SECONDS))

        if not self.region:
            raise ConfigurationError("`region` is required (e.g. mypurecloud.com, usw2.pure.cloud).")
        if not self.client_id or not self.client_secret:
            raise ConfigurationError("`client_id` and `client_secret` are required.")

        # Low-cardinality tags only. Never tag by conversation_id.
        self.base_tags = ["region:{}".format(self.region)]
        self.base_tags.extend(self.instance.get("tags", []))

    def check(self, _):
        interval = self._query_interval()

        try:
            analytics_api = self._authenticate()
            conversations = self._collect_conversations(analytics_api, interval)
        except Exception:
            # Report connectivity as a 0/1 gauge rather than a service check.
            self.gauge(self.CAN_CONNECT_METRIC, 0, tags=self.base_tags)
            self.log.exception("Genesys Cloud MOS collection failed")
            raise

        self.gauge(self.CAN_CONNECT_METRIC, 1, tags=self.base_tags)
        self._submit_metrics(conversations)

    def _query_interval(self):
        """Trailing, interval-length window offset by a lag so ended conversations
        have been indexed by Genesys. Consecutive runs cover ~disjoint windows,
        which avoids double-counting the distribution across runs."""
        now = datetime.now(timezone.utc)
        end = now - timedelta(seconds=self.lag_seconds)
        start = end - timedelta(seconds=self.window_seconds)
        fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
        return "{}/{}".format(start.strftime(fmt), end.strftime(fmt))

    def _authenticate(self):
        """Authenticate with the client-credentials grant and return an AnalyticsApi.
        A fresh token is fetched each run, so no long-lived refresh logic is needed.
        Isolated for testability (patched in unit tests)."""
        import PureCloudPlatformClientV2 as genesys

        genesys.configuration.Configuration().host = "https://api.{}".format(self.region)
        api_client = genesys.api_client.ApiClient().get_client_credentials_token(self.client_id, self.client_secret)
        return genesys.AnalyticsApi(api_client)

    def _collect_conversations(self, analytics_api, interval):
        """Page through the conversation detail query and return {conversation_id: mos}.
        Dedupes by conversation_id to guard against overlap between pages/windows."""
        import PureCloudPlatformClientV2 as genesys

        mos_predicate = genesys.ConversationDetailQueryPredicate()
        mos_predicate.dimension = MOS_DIMENSION
        mos_predicate.operator = "exists"

        end_predicate = genesys.ConversationDetailQueryPredicate()
        end_predicate.dimension = CONVERSATION_END_DIMENSION
        end_predicate.operator = "exists"

        conversation_filter = genesys.ConversationDetailQueryFilter()
        conversation_filter.type = "and"
        conversation_filter.predicates = [mos_predicate, end_predicate]

        collected = {}
        page_number = 1
        while True:
            body = genesys.ConversationQuery()
            body.interval = interval
            body.conversation_filters = [conversation_filter]
            paging = genesys.PagingSpec()
            paging.page_size = PAGE_SIZE
            paging.page_number = page_number
            body.paging = paging

            response = analytics_api.post_analytics_conversations_details_query(body)
            conversations = getattr(response, "conversations", None)
            if not conversations:
                break

            for conversation in conversations:
                mos = getattr(conversation, "media_stats_min_conversation_mos", None)
                conversation_id = getattr(conversation, "conversation_id", None)
                if mos is None or conversation_id is None:
                    continue
                collected[conversation_id] = float(mos)

            page_number += 1

        return collected

    def _submit_metrics(self, conversations):
        count = len(conversations)
        self.gauge("conversation.count", count, tags=self.base_tags)

        values = list(conversations.values())
        below_threshold = sum(1 for mos in values if mos <= self.mos_threshold)
        self.gauge("conversation.below_threshold.count", below_threshold, tags=self.base_tags)

        # Only emit quality gauges when there is data; emitting 0 would look like a
        # catastrophic MOS rather than "no conversations in the window".
        if count:
            self.gauge("conversation.mos.avg", sum(values) / count, tags=self.base_tags)
            self.gauge("conversation.mos.min", min(values), tags=self.base_tags)

        self.log.debug(
            "Genesys MOS: %d conversations, %d at/below threshold %.2f",
            count,
            below_threshold,
            self.mos_threshold,
        )

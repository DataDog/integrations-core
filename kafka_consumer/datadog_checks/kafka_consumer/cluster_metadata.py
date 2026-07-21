# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Kafka Cluster Metadata Collection."""

import concurrent.futures
import hashlib
import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, NotRequired, TypedDict
from urllib.parse import quote

from confluent_kafka import IsolationLevel, KafkaException, TopicPartition
from confluent_kafka.admin import ConfigResource, OffsetSpec, ResourceType

from datadog_checks.kafka_consumer.cache import CacheHelper
from datadog_checks.kafka_consumer.connectors import _build_http_kwargs
from datadog_checks.kafka_consumer.constants import KAFKA_INTERNAL_TOPICS

CONSUMER_GROUP_REBALANCING_STATES = frozenset({'PREPARING_REBALANCING', 'COMPLETING_REBALANCING'})


class SchemaDefinition(TypedDict):
    schema: str
    schema_type: str


class SubjectVersionInfo(TypedDict):
    version: int
    schema_id: int
    compatibility: NotRequired[str | None]


class SchemaInfo(TypedDict):
    schema_content: str
    topic_name: str
    schema_for: str
    schema_version: int | None
    schema_id: int | None
    schema_type: str
    compatibility: str | None


class ClusterMetadataCollector:
    """Collects Kafka cluster metadata (brokers, topics, consumer groups, schemas)."""

    def __init__(self, check, client, config, log):
        self.check = check
        self.client = client
        self.config = config
        self.log = log
        self.http = check.http

        self.cache = CacheHelper(check, log, config._kafka_configs_refresh_interval)
        self.BROKER_CONFIG_BATCH_SIZE = 5  # Max brokers to describe_configs per run (one per call, Kafka limitation)
        self.TOPIC_CONFIG_BATCH_SIZE = 100  # Max topics to describe_configs per check run

        self.SCHEMA_VERSION_CHECK_BATCH_SIZE = 200  # Lightweight calls, can do more per run
        self.SCHEMA_COMPATIBILITY_BATCH_SIZE = 200  # Lightweight calls, refreshed on configs cadence
        self.SCHEMA_FETCH_CONCURRENCY = 10  # Parallel HTTP requests

        # Cache size limits
        self.BROKER_CONFIG_CACHE_MAX_SIZE = 1_000
        self.TOPIC_CONFIG_CACHE_MAX_SIZE = 20_000
        self.SCHEMA_VERSION_CHECK_CACHE_MAX_SIZE = 20_000
        self.SCHEMA_COMPATIBILITY_FETCH_CACHE_MAX_SIZE = 20_000
        self.SCHEMA_ID_CACHE_MAX_SIZE = 20_000

        self.EARLIEST_OFFSETS_DEFAULT_TTL = 300  # 5 minutes, matches Kafka's own broker default
        self.EARLIEST_OFFSETS_MIN_TTL = 60
        self.EARLIEST_OFFSETS_MAX_TTL = 1800
        self._log_retention_check_interval_s: float | None = None

        self.BROKER_CONFIG_CACHE_KEY = 'kafka_broker_config_cache'
        self.BROKER_CONFIG_FETCH_CACHE_KEY = 'kafka_broker_config_fetch_cache'
        self.EARLIEST_OFFSETS_CACHE_KEY = 'kafka_earliest_offsets_cache'
        self.TOPIC_CONFIG_CACHE_KEY = 'kafka_topic_config_cache'
        self.TOPIC_CONFIG_FETCH_CACHE_KEY = 'kafka_topic_config_fetch_cache'
        self.TOPIC_HWM_SUM_CACHE_KEY = 'kafka_topic_hwm_sum_cache'
        self.CONSUMER_GROUP_MEMBERS_CACHE_KEY = 'kafka_consumer_group_members_cache'
        self.SCHEMA_CACHE_KEY = 'kafka_schema_cache'
        self.SCHEMA_VERSION_CHECK_CACHE_KEY = 'kafka_schema_version_check_cache'
        self.SCHEMA_COMPATIBILITY_FETCH_CACHE_KEY = 'kafka_schema_compatibility_fetch_cache'
        self.SCHEMA_LATEST_VERSION_CACHE_KEY = 'kafka_schema_latest_version_cache'
        self.SCHEMA_ID_CACHE_KEY = 'kafka_schema_id_cache'
        self.GLOBAL_COMPATIBILITY_CACHE_KEY = 'kafka_schema_global_compatibility_cache'
        self.SCRAM_CREDENTIAL_CACHE_KEY = 'kafka_scram_credential_cache'
        self.SCRAM_CREDENTIAL_CACHE_MAX_SIZE = 20_000

        self._schema_registry_oauth_token: str | None = None
        self._schema_registry_oauth_token_expiry: float = 0.0
        self._schema_registry_http_kwargs: dict[str, Any] = {}

        if self.config._collect_schema_registry:
            self._build_schema_registry_http_kwargs()

    def _build_schema_registry_http_kwargs(self) -> None:
        """Build per-request HTTP kwargs for Schema Registry auth and TLS."""
        self._schema_registry_http_kwargs = _build_http_kwargs(
            self.config._schema_registry_username,
            self.config._schema_registry_password,
            self.config._schema_registry_tls_verify,
            self.config._schema_registry_tls_ca_cert,
            self.config._schema_registry_tls_cert,
            self.config._schema_registry_tls_key,
        )

    def _get_schema_registry_request_kwargs(self) -> dict[str, Any]:
        """Return per-request kwargs including the current OAuth bearer token if set."""
        kwargs: dict[str, Any] = dict(self._schema_registry_http_kwargs)
        if self._schema_registry_oauth_token:
            extra_headers: dict[str, str] = {'Authorization': f'Bearer {self._schema_registry_oauth_token}'}
            oauth_config = self.config._schema_registry_oauth_token_provider
            if oauth_config:
                custom_headers = oauth_config.get('custom_headers')
                if custom_headers:
                    extra_headers.update(custom_headers)
            kwargs['extra_headers'] = extra_headers
        return kwargs

    def _refresh_schema_registry_oauth_token(self) -> None:
        """Fetch or refresh the OAuth token for Schema Registry if configured and expired."""
        oauth_config = self.config._schema_registry_oauth_token_provider
        if not oauth_config:
            return

        if self._schema_registry_oauth_token and time.time() < (self._schema_registry_oauth_token_expiry - 30):
            return

        token, expires_at = self._fetch_oidc_token(oauth_config)
        self._schema_registry_oauth_token = token
        self._schema_registry_oauth_token_expiry = expires_at
        self.log.debug("Schema Registry OAuth token refreshed, expires at %s", expires_at)

    def _fetch_oidc_token(self, oauth_config: dict) -> tuple[str, float]:
        """Fetch an OIDC token using client credentials grant."""
        token_url = oauth_config["url"]
        client_id = oauth_config["client_id"]
        client_secret = oauth_config["client_secret"]

        data = {"grant_type": "client_credentials"}
        scope = oauth_config.get("scope")
        if scope:
            data["scope"] = scope

        options = {}
        tls_ca_cert = oauth_config.get("tls_ca_cert")
        if tls_ca_cert:
            options["verify"] = tls_ca_cert

        response = self.http.post(
            token_url,
            data=data,
            auth=(client_id, client_secret),
            **options,
        )
        response.raise_for_status()
        token_data = response.json()

        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 300)
        expires_at = time.time() + expires_in

        return access_token, expires_at

    def _schema_registry_get(self, path: str, **extra_kwargs: Any) -> Any:
        """GET a Schema Registry path and return the parsed JSON body."""
        url = f"{self.config._collect_schema_registry}{path}"
        kwargs = {**self._get_schema_registry_request_kwargs(), **extra_kwargs}
        response = self.http.get(url, **kwargs)
        response.raise_for_status()
        return response.json()

    def _get_schema_registry_subjects(self):
        return self._schema_registry_get('/subjects')

    def _get_schema_registry_versions(self, subject: str) -> list[int]:
        """Fetch the list of version numbers for a subject (lightweight call)."""
        encoded_subject = quote(subject, safe='')
        return self._schema_registry_get(f'/subjects/{encoded_subject}/versions')

    def _get_schema_registry_latest_version(self, subject):
        encoded_subject = quote(subject, safe='')
        return self._schema_registry_get(f'/subjects/{encoded_subject}/versions/latest')

    def _get_schema_registry_global_compatibility(self) -> str | None:
        """Return the global compatibility level from the Schema Registry."""
        return self._schema_registry_get('/config').get('compatibilityLevel')

    def _get_schema_registry_subject_compatibility(self, subject: str) -> str | None:
        """Return the effective compatibility for a subject, falling back to global."""
        encoded_subject = quote(subject, safe='')
        return self._schema_registry_get(
            f'/config/{encoded_subject}',
            params={'defaultToGlobal': 'true'},
        ).get('compatibilityLevel')

    def _parallel_fetch(self, fn: Callable[[str], Any], subjects: list[str], error_label: str) -> dict[str, Any]:
        """Run fn(subject) for each subject concurrently; drop and log individual failures."""
        results: dict[str, Any] = {}
        if not subjects:
            return results
        with ThreadPoolExecutor(max_workers=self.SCHEMA_FETCH_CONCURRENCY) as executor:
            future_to_subject = {executor.submit(fn, subject): subject for subject in subjects}
            for future in as_completed(future_to_subject):
                subject = future_to_subject[future]
                try:
                    results[subject] = future.result()
                except Exception as e:
                    self.log.warning("Error fetching %s for %s: %s", error_label, subject, e)
        return results

    def collect_all_metadata(self, highwater_offsets, low_watermark_offsets, topic_partitions):
        try:
            shared_metadata = self.client.kafka_client.list_topics(timeout=self.config._request_timeout)
        except Exception as e:
            self.log.debug("Could not prefetch cluster metadata: %s", e)
            shared_metadata = None

        try:
            self._collect_broker_metadata(shared_metadata)
        except Exception as e:
            self.log.error("Error collecting broker metadata: %s", e)

        try:
            self._collect_topic_metadata(shared_metadata, highwater_offsets, low_watermark_offsets, topic_partitions)
        except Exception as e:
            self.log.error("Error collecting topic metadata: %s", e)

        try:
            self._collect_consumer_group_metadata(shared_metadata)
        except Exception as e:
            self.log.error("Error collecting consumer group metadata: %s", e)

        try:
            self._collect_schema_registry_info(shared_metadata)
        except Exception as e:
            self.log.error("Error collecting schema registry info: %s", e)

        try:
            self._collect_scram_credentials(shared_metadata)
        except Exception as e:
            self.log.error("Error collecting SCRAM credentials: %s", e)

    def _collect_broker_metadata(self, metadata=None):
        self.log.debug("Collecting broker metadata")

        if metadata is None:
            try:
                metadata = self.client.kafka_client.list_topics(timeout=self.config._request_timeout)
            except Exception as e:
                self.log.debug("Could not list topics for broker metadata: %s", e)
                return

        brokers = metadata.brokers
        cluster_id = self.config._kafka_cluster_id_override or (
            metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
        )

        self.log.debug("Found %s brokers in cluster %s", len(brokers), cluster_id)
        broker_tags = self.config._get_tags(cluster_id) + [f'bootstrap_servers:{self.config._kafka_connect_str}']
        self.check.gauge('broker.count', len(brokers), tags=broker_tags)

        try:
            cluster_future = self.client.kafka_client.describe_cluster()
            cluster_info = cluster_future.result(timeout=self.config._request_timeout)

            if cluster_info.controller:
                controller_tags = self.config._get_tags(cluster_id) + [
                    f'controller_id:{cluster_info.controller.id}',
                    f'controller_host:{cluster_info.controller.host}',
                    f'controller_port:{cluster_info.controller.port}',
                ]
                # Emit metric indicating which broker is the controller (value is controller_id)
                self.check.gauge('cluster.controller_id', cluster_info.controller.id, tags=controller_tags)
        except Exception as e:
            self.log.debug("Could not collect controller information: %s", e)

        broker_leader_count = dict.fromkeys(brokers.keys(), 0)
        broker_partition_count = dict.fromkeys(brokers.keys(), 0)

        for topic_name, topic_metadata in metadata.topics.items():
            if topic_name in KAFKA_INTERNAL_TOPICS:
                continue
            for _partition_id, partition_metadata in topic_metadata.partitions.items():
                if partition_metadata.leader in broker_leader_count:
                    broker_leader_count[partition_metadata.leader] += 1
                for replica in partition_metadata.replicas:
                    if replica in broker_partition_count:
                        broker_partition_count[replica] += 1

        # Emit per-broker metrics (fast, in-memory only)
        for broker_id, broker_metadata in brokers.items():
            tags = self.config._get_tags(cluster_id) + [
                f'broker_id:{broker_id}',
                f'broker_host:{broker_metadata.host}',
                f'broker_port:{broker_metadata.port}',
            ]
            self.check.gauge('broker.leader_count', broker_leader_count.get(broker_id, 0), tags=tags)
            self.check.gauge('broker.partition_count', broker_partition_count.get(broker_id, 0), tags=tags)

        broker_ids_to_fetch = self.cache.get_items_to_fetch(
            self.BROKER_CONFIG_FETCH_CACHE_KEY, [str(bid) for bid in brokers.keys()]
        )
        fetched_broker_configs = {}
        broker_ids_batch = []

        if broker_ids_to_fetch:
            broker_ids_batch = broker_ids_to_fetch[: self.BROKER_CONFIG_BATCH_SIZE]
            self.log.debug(
                "Fetching configs for %d/%d brokers",
                len(broker_ids_batch),
                len(broker_ids_to_fetch),
            )

            for broker_id_str in broker_ids_batch:
                broker_meta = brokers.get(int(broker_id_str))
                if not broker_meta:
                    continue

                metric_tags = self.config._get_tags(cluster_id) + [
                    f'broker_id:{broker_id_str}',
                    f'broker_host:{broker_meta.host}',
                    f'broker_port:{broker_meta.port}',
                ]

                try:
                    resources = [ConfigResource(ResourceType.BROKER, broker_id_str)]
                    futures = self.client.kafka_client.describe_configs(resources)
                    config_entries = futures[resources[0]].result(timeout=self.config._request_timeout)
                except Exception as e:
                    self.log.warning("Failed to describe configs for broker %s: %s", broker_id_str, e)
                    continue

                config_data = {}
                for config_name, config_entry in config_entries.items():
                    config_data[config_name] = config_entry.value

                for config_name in [
                    'log.retention.bytes',
                    'log.retention.ms',
                    'log.segment.bytes',
                    'num.partitions',
                    'num.network.threads',
                    'num.io.threads',
                    'default.replication.factor',
                    'min.insync.replicas',
                ]:
                    if config_name in config_data:
                        try:
                            value = float(config_data[config_name]) if config_data[config_name] else 0
                            metric_name = f"broker.config.{config_name.replace('.', '_')}"
                            self.check.gauge(metric_name, value, tags=metric_tags)
                        except (ValueError, TypeError):
                            self.log.debug(
                                "Could not convert broker %s config %s value %r to float",
                                broker_id_str,
                                config_name,
                                config_data[config_name],
                            )

                retention_check_interval_ms = config_data.get('log.retention.check.interval.ms')
                if retention_check_interval_ms:
                    try:
                        interval_s = float(retention_check_interval_ms) / 1000
                        if interval_s > 0:
                            self._log_retention_check_interval_s = min(
                                interval_s, self._log_retention_check_interval_s or interval_s
                            )
                    except (ValueError, TypeError):
                        self.log.debug(
                            "Could not convert broker %s config log.retention.check.interval.ms value %r to float",
                            broker_id_str,
                            retention_check_interval_ms,
                        )

                truncated_config = self._truncate_config_for_event(config_data, max_configs=50)
                event_text = json.dumps(truncated_config, indent=2, sort_keys=True)

                fetched_broker_configs[broker_id_str] = {
                    'event_text': event_text,
                    'broker_host': broker_meta.host,
                    'broker_port': broker_meta.port,
                }

        self.cache.mark_items_fetched(
            self.BROKER_CONFIG_FETCH_CACHE_KEY,
            broker_ids_batch,
            ttl_base=self.cache.refresh_interval,
            ttl_jitter=self.cache.refresh_jitter,
            max_cache_size=self.BROKER_CONFIG_CACHE_MAX_SIZE,
        )

        broker_contents = {bid: info['event_text'] for bid, info in fetched_broker_configs.items()}
        brokers_to_emit = self.cache.get_events_to_send(self.BROKER_CONFIG_CACHE_KEY, broker_contents)

        for broker_id in brokers_to_emit:
            info = fetched_broker_configs[broker_id]
            self.check.event_platform_event(
                json.dumps(
                    {
                        'collection_timestamp': int(time.time() * 1000),
                        'kafka_cluster_id': cluster_id,
                        **self.config._original_cluster_id_field(),
                        'broker_id': str(broker_id),
                        'broker_host': info['broker_host'],
                        'broker_port': info['broker_port'],
                        'config_type': 'broker',
                        'config': json.loads(info['event_text']),
                    }
                ),
                "data-streams-message",
            )

    def _topic_partition_pairs(self, topic_partitions):
        return {
            (topic, partition)
            for topic, partitions in topic_partitions.items()
            if topic not in KAFKA_INTERNAL_TOPICS
            for partition in partitions
        }

    def _earliest_offsets_ttl(self) -> float:
        """TTL for the earliest-offsets cache, derived from the broker's log-cleaner cycle."""
        ttl = self._log_retention_check_interval_s or self.EARLIEST_OFFSETS_DEFAULT_TTL
        return max(self.EARLIEST_OFFSETS_MIN_TTL, min(self.EARLIEST_OFFSETS_MAX_TTL, ttl))

    def _load_earliest_offsets_cache(self) -> dict[str, Any] | None:
        try:
            cached_str = self.check.read_persistent_cache(self.EARLIEST_OFFSETS_CACHE_KEY)
            if not cached_str:
                return None
            data = json.loads(cached_str)
            return {
                'expire_at': data['expire_at'],
                'offsets': {(topic, partition): offset for topic, partition, offset in data['offsets']},
            }
        except Exception as e:
            self.log.debug("Could not read earliest offsets cache: %s", e)
            return None

    def _save_earliest_offsets_cache(self, offsets: dict[tuple[str, int], int], expire_at: float | None = None) -> None:
        try:
            payload = {
                'expire_at': expire_at if expire_at is not None else time.time() + self._earliest_offsets_ttl(),
                'offsets': [[topic, partition, offset] for (topic, partition), offset in offsets.items()],
            }
            self.check.write_persistent_cache(self.EARLIEST_OFFSETS_CACHE_KEY, json.dumps(payload))
        except Exception as e:
            self.log.debug("Could not write earliest offsets cache: %s", e)

    def fetch_earliest_offsets(self, topic_partitions):
        """Return cached log-start offsets, refetching from the broker only once the TTL expires."""
        requested = self._topic_partition_pairs(topic_partitions)
        if not requested:
            return {}

        cached = self._load_earliest_offsets_cache()
        if cached is not None and time.time() < cached['expire_at']:
            cached_offsets = {tp: offset for tp, offset in cached['offsets'].items() if tp in requested}
            if cached_offsets.keys() == requested:
                return cached_offsets

            result = self._fetch_earliest_offsets_from_broker(topic_partitions)
            if result:
                self._save_earliest_offsets_cache(result, expire_at=cached['expire_at'])
            return result

        result = self._fetch_earliest_offsets_from_broker(topic_partitions)
        if result:
            self._save_earliest_offsets_cache(result)
        return result

    def _fetch_earliest_offsets_from_broker(self, topic_partitions):
        """Batch-fetch log-start offsets via AdminClient.list_offsets(earliest).

        Uses ListOffsets with the EARLIEST_TIMESTAMP sentinel, which the broker
        services from in-memory state without scanning .timeindex segment files.
        Failures are logged and surface as missing entries — the caller skips
        the earliest-dependent metrics rather than aborting the whole topic
        metadata collection.
        """
        requests = {
            TopicPartition(topic, partition): OffsetSpec.earliest()
            for topic, partition in self._topic_partition_pairs(topic_partitions)
        }
        if not requests:
            return {}

        result = {}
        errors = 0
        try:
            futures = self.client.kafka_client.list_offsets(
                requests,
                isolation_level=IsolationLevel.READ_UNCOMMITTED,
                request_timeout=self.config._request_timeout,
            )
            for tp, future in futures.items():
                try:
                    info = future.result()
                    result[(tp.topic, tp.partition)] = info.offset
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        self.log.debug(
                            "Failed to fetch earliest offset for %s:%s: %s",
                            tp.topic,
                            tp.partition,
                            e,
                        )
        except Exception as e:
            self.log.warning(
                "Failed to issue list_offsets request; partition.beginning_offset, "
                "partition.size, and topic.size will be skipped this run: %s",
                e,
            )
            return {}
        if errors:
            self.log.warning(
                "Failed to fetch earliest offset for %d/%d partitions; "
                "earliest-dependent metrics will be skipped for those partitions",
                errors,
                len(requests),
            )
        return result

    def _collect_topic_metadata(self, metadata, highwater_offsets, low_watermark_offsets, topic_partitions):
        self.log.debug("Collecting topic metadata")

        cluster_id = self.config._kafka_cluster_id_override or (
            metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
        )
        all_topics_metadata = metadata.topics

        self.log.debug("Found %s topics", len(topic_partitions))

        self.check.gauge('topic.count', len(topic_partitions), tags=self.config._get_tags(cluster_id))

        now_ts = time.time()
        prev_ts = None
        previous_partition_offsets = {}
        try:
            prev_hwm_cache_str = self.check.read_persistent_cache(self.TOPIC_HWM_SUM_CACHE_KEY)
            if prev_hwm_cache_str:
                prev_payload = json.loads(prev_hwm_cache_str)
                prev_ts = float(prev_payload.get('ts'))
                previous_partition_offsets = prev_payload.get('partitions') or {}
        except Exception as e:
            self.log.debug("Could not read topic HWM cache: %s", e)

        current_partition_offsets = {}

        for topic_name, partitions in topic_partitions.items():
            if topic_name in KAFKA_INTERNAL_TOPICS:
                continue

            topic_tags = self.config._get_tags(cluster_id) + [f'topic:{topic_name}']

            if not partitions:
                self.log.warning("No partitions found for topic %s", topic_name)
                continue

            self.check.gauge('topic.partitions', len(partitions), tags=topic_tags)

            total_messages = 0
            have_all_earliest = True
            topic_metadata = all_topics_metadata.get(topic_name)

            if not topic_metadata:
                self.log.warning("No metadata found for topic %s", topic_name)
                continue

            for partition_id in partitions:
                partition_tags = topic_tags + [f'partition:{partition_id}']

                partition_metadata = topic_metadata.partitions.get(partition_id)
                latest = highwater_offsets.get((topic_name, partition_id), 0)
                earliest = low_watermark_offsets.get((topic_name, partition_id))

                if earliest is None:
                    have_all_earliest = False
                    partition_size = None
                else:
                    partition_size = max(0, latest - earliest)
                    total_messages += partition_size
                    self.check.gauge('partition.beginning_offset', earliest, tags=partition_tags)

                if partition_metadata:
                    leader = partition_metadata.leader
                    replicas = partition_metadata.replicas
                    isrs = partition_metadata.isrs

                    partition_broker_tags = partition_tags + [f'leader_broker_id:{leader}']
                    for replica in replicas:
                        partition_broker_tags.append(f'replica_broker_id:{replica}')

                    isr_set = set(isrs)
                    out_of_sync_broker_ids = [broker_id for broker_id in replicas if broker_id not in isr_set]
                    for broker_id in out_of_sync_broker_ids:
                        partition_broker_tags.append(f'out_of_sync_broker_id:{broker_id}')

                    self.check.gauge('partition.replicas', len(replicas), tags=partition_broker_tags)
                    self.check.gauge('partition.isr', len(isrs), tags=partition_broker_tags)

                    if partition_size is not None:
                        self.check.gauge('partition.size', partition_size, tags=partition_broker_tags)

                    is_under_replicated = bool(out_of_sync_broker_ids)
                    self.check.gauge(
                        'partition.under_replicated',
                        1 if is_under_replicated else 0,
                        tags=partition_broker_tags,
                    )

                    is_offline = leader == -1
                    self.check.gauge('partition.offline', 1 if is_offline else 0, tags=partition_broker_tags)
                elif partition_size is not None:
                    self.check.gauge('partition.size', partition_size, tags=partition_tags)

            if have_all_earliest:
                self.check.gauge('topic.size', total_messages, tags=topic_tags)

            # Calculate topic throughput
            sum_latest = 0
            sum_previous = 0
            for partition_id in partitions:
                partition_key = f"{topic_name}:{partition_id}"
                current_offset = highwater_offsets.get((topic_name, partition_id), -1)

                if current_offset < 0:
                    self.log.debug(
                        "Partition %s:%s is unavailable (offset: %s), using previous offset for throughput",
                        topic_name,
                        partition_id,
                        current_offset,
                    )
                    # Retain previous valid offset in cache for when partition becomes available again
                    if partition_key in previous_partition_offsets:
                        current_partition_offsets[partition_key] = previous_partition_offsets[partition_key]
                    continue

                current_partition_offsets[partition_key] = current_offset

                # Check for offset decrease (data loss scenario)
                if partition_key in previous_partition_offsets:
                    previous_offset = previous_partition_offsets[partition_key]
                    if current_offset < previous_offset:
                        self.log.debug(
                            "Detected offset decrease for partition %s:%s (was %s, now %s). "
                            "This may indicate data loss. "
                            "Resetting baseline for throughput calculation.",
                            topic_name,
                            partition_id,
                            previous_offset,
                            current_offset,
                        )
                        continue
                    sum_latest += current_offset
                    sum_previous += previous_offset
                else:
                    # New partition, don't include in throughput to avoid
                    # huge fake spike in traffic when integration is started
                    pass

            if prev_ts and (now_ts - prev_ts) > 0:
                message_rate = (sum_latest - sum_previous) / (now_ts - prev_ts)
                self.check.gauge('topic.message_rate', message_rate, tags=topic_tags)

        # --- Topic config fetching (batched describe_configs) ---
        all_topic_names = [name for name in topic_partitions.keys() if name not in KAFKA_INTERNAL_TOPICS]
        topic_names_to_fetch = self.cache.get_items_to_fetch(self.TOPIC_CONFIG_FETCH_CACHE_KEY, all_topic_names)

        # Batch: cap the number of topic configs fetched per check run.
        topic_names_to_fetch = topic_names_to_fetch[: self.TOPIC_CONFIG_BATCH_SIZE]

        fetched_topic_configs = {}

        if topic_names_to_fetch:
            self.log.debug("Fetching configs for %d topics", len(topic_names_to_fetch))

            # Single batched describe_configs call for all topics at once
            resources = [ConfigResource(ResourceType.TOPIC, name) for name in topic_names_to_fetch]
            futures = self.client.kafka_client.describe_configs(resources)

            for resource, future in futures.items():
                topic_name = resource.name
                topic_tags = self.config._get_tags(cluster_id) + [f'topic:{topic_name}']

                try:
                    config_result = future.result(timeout=self.config._request_timeout)
                except Exception as e:
                    self.log.warning("Failed to describe configs for topic %s: %s", topic_name, e)
                    continue

                if not config_result:
                    continue

                topic_config = {}
                for config_name, config_entry in config_result.items():
                    topic_config[config_name] = config_entry.value

                if not topic_config:
                    continue

                if 'retention.ms' in topic_config and topic_config['retention.ms'] != '-1':
                    retention_ms = int(topic_config['retention.ms'])
                    self.check.gauge('topic.config.retention_ms', retention_ms, tags=topic_tags)

                if 'retention.bytes' in topic_config and topic_config['retention.bytes'] != '-1':
                    retention_bytes = int(topic_config['retention.bytes'])
                    self.check.gauge('topic.config.retention_bytes', retention_bytes, tags=topic_tags)

                if 'max.message.bytes' in topic_config:
                    max_bytes = int(topic_config['max.message.bytes'])
                    self.check.gauge('topic.config.max_message_bytes', max_bytes, tags=topic_tags)

                truncated_config = self._truncate_config_for_event(topic_config, max_configs=30)
                event_text = json.dumps(truncated_config, indent=2, sort_keys=True)

                fetched_topic_configs[topic_name] = {
                    'event_text': event_text,
                }

        self.cache.mark_items_fetched(
            self.TOPIC_CONFIG_FETCH_CACHE_KEY,
            topic_names_to_fetch,
            ttl_base=self.cache.refresh_interval,
            ttl_jitter=self.cache.refresh_jitter,
            max_cache_size=self.TOPIC_CONFIG_CACHE_MAX_SIZE,
        )

        topic_contents = {name: info['event_text'] for name, info in fetched_topic_configs.items()}
        topics_to_emit = self.cache.get_events_to_send(self.TOPIC_CONFIG_CACHE_KEY, topic_contents)

        for topic_name in topics_to_emit:
            info = fetched_topic_configs[topic_name]
            self.check.event_platform_event(
                json.dumps(
                    {
                        'collection_timestamp': int(time.time() * 1000),
                        'kafka_cluster_id': cluster_id,
                        **self.config._original_cluster_id_field(),
                        'topic': topic_name,
                        'config_type': 'topic',
                        'config': json.loads(info['event_text']),
                    }
                ),
                "data-streams-message",
            )

        try:
            snapshot = {'ts': float(now_ts), 'partitions': current_partition_offsets}
            self.check.write_persistent_cache(self.TOPIC_HWM_SUM_CACHE_KEY, json.dumps(snapshot))
        except Exception as e:
            self.log.debug("Could not write topic HWM cache: %s", e)

    def _collect_consumer_group_metadata(self, metadata):
        self.log.debug("Collecting consumer group metadata")
        cluster_id = self.config._kafka_cluster_id_override or (
            metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
        )
        consumer_groups_future = self.client.kafka_client.list_consumer_groups()
        consumer_groups_result = consumer_groups_future.result(timeout=self.config._request_timeout)

        if consumer_groups_result.errors:
            self.log.warning("Errors listing consumer groups: %s", consumer_groups_result.errors)

        consumer_groups = consumer_groups_result.valid

        self.log.debug("Found %s consumer groups", len(consumer_groups))
        self.check.gauge('consumer_group.count', len(consumer_groups), tags=self.config._get_tags(cluster_id))

        group_ids = [group.group_id for group in consumer_groups]
        if not group_ids:
            return
        describe_futures = self.client.kafka_client.describe_consumer_groups(group_ids)

        group_id_to_info = {}
        for group_id, future in describe_futures.items():
            try:
                group_id_to_info[group_id] = future.result(timeout=self.config._request_timeout)
            except Exception as e:
                self.log.warning("Error getting consumer group details for %s: %s", group_id, e)

        prev_member_hashes = self._load_member_hashes_cache()
        current_member_hashes = {}

        for group_id, group_info in group_id_to_info.items():
            group_tags = self.config._get_tags(cluster_id) + [f'consumer_group:{group_id}']
            state = group_info.state
            members = group_info.members
            coordinator = group_info.coordinator
            state_name = state.name if hasattr(state, 'name') else str(state)
            state_tags = group_tags + [f'consumer_group_state:{state_name}']
            if coordinator:
                state_tags.append(f'coordinator:{coordinator.id}')

            # All group-level gauges share the same tag set so they can be correlated in dashboards.
            group_meta_tags = self._build_group_meta_tags(state_tags, group_info)

            self.check.gauge('consumer_group.members', len(members), tags=group_meta_tags)
            self.check.gauge(
                'consumer_group.rebalancing',
                1 if self._is_group_rebalancing(state_name, members) else 0,
                tags=group_meta_tags,
            )

            member_ids = sorted(getattr(m, 'member_id', '') or '' for m in members)
            member_hash = hashlib.sha256(json.dumps(member_ids, separators=(',', ':')).encode()).hexdigest()
            current_member_hashes[group_id] = member_hash

            if prev_member_hashes is not None:
                prev_hash = prev_member_hashes.get(group_id)
                if prev_hash is not None and prev_hash != member_hash:
                    self.check.count('consumer_group.membership_changes', 1, tags=group_meta_tags)

            for member in members:
                client_id = member.client_id
                host = member.host

                if hasattr(member, 'assignment') and member.assignment:
                    partition_count = len(member.assignment.topic_partitions)

                    # Member-level gauges deliberately use state_tags, not group_meta_tags: the
                    # group-level dimensional tags are omitted here to keep per-member cardinality bounded.
                    member_tags = state_tags + [
                        f'client_id:{client_id}',
                        f'member_host:{host}',
                    ]
                    group_instance_id = getattr(member, 'group_instance_id', None)
                    if group_instance_id is not None:
                        member_tags.append(f'group_instance_id:{group_instance_id}')
                    self.check.gauge('consumer_group.member.partitions', partition_count, tags=member_tags)

        self._save_member_hashes_cache(current_member_hashes)

    def _collect_scram_credentials(self, metadata) -> None:
        """Collect the SASL/SCRAM credential inventory: a per-mechanism count metric and per-credential events."""
        self.log.debug("Collecting SCRAM credentials")

        try:
            future = self.client.kafka_client.describe_user_scram_credentials()
            descriptions = future.result(timeout=self.config._request_timeout)
        except (KafkaException, concurrent.futures.TimeoutError) as e:
            # Clusters without SCRAM configured, or brokers that don't support the API, raise here.
            # This is expected, so skip gracefully without failing other metadata collection.
            self.log.debug("Could not collect SCRAM credentials: %s", e)
            return

        cluster_id = self.config._kafka_cluster_id_override or (
            metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
        )

        mechanism_counts: dict[str, int] = {}
        credential_events: dict[str, str] = {}
        credential_payloads: dict[str, dict[str, Any]] = {}

        for user, description in descriptions.items():
            for credential_info in description.scram_credential_infos:
                mechanism = credential_info.mechanism
                mechanism_name = (mechanism.name if hasattr(mechanism, 'name') else str(mechanism)).lower()
                mechanism_counts[mechanism_name] = mechanism_counts.get(mechanism_name, 0) + 1
                payload = {
                    'user': user,
                    'mechanism': mechanism_name,
                    'iterations': credential_info.iterations,
                }
                cache_key = f'{user}:{mechanism_name}'
                credential_payloads[cache_key] = payload
                credential_events[cache_key] = json.dumps(payload, sort_keys=True)

        for mechanism_name, count in mechanism_counts.items():
            self.check.gauge(
                'scram_credentials.count',
                count,
                tags=self.config._get_tags(cluster_id) + [f'mechanism:{mechanism_name}'],
            )

        credentials_to_emit = self.cache.get_events_to_send(
            self.SCRAM_CREDENTIAL_CACHE_KEY, credential_events, max_cache_size=self.SCRAM_CREDENTIAL_CACHE_MAX_SIZE
        )

        for cache_key in credentials_to_emit:
            payload = credential_payloads[cache_key]
            self.check.event_platform_event(
                json.dumps(
                    {
                        'collection_timestamp': int(time.time() * 1000),
                        'kafka_cluster_id': cluster_id,
                        **self.config._original_cluster_id_field(),
                        'user': payload['user'],
                        'mechanism': payload['mechanism'],
                        'iterations': payload['iterations'],
                        'config_type': 'scram_credential',
                    }
                ),
                "data-streams-message",
            )

    def _load_member_hashes_cache(self) -> dict[str, str] | None:
        """Return the previous member-hash map, or None if unreadable."""
        try:
            cached = self.check.read_persistent_cache(self.CONSUMER_GROUP_MEMBERS_CACHE_KEY)
            if not cached:
                return None
            result = json.loads(cached)
            if not isinstance(result, dict):
                self.log.debug("Consumer group members cache has unexpected shape; discarding")
                return None
            return result
        except Exception as e:
            self.log.debug("Could not read consumer group members cache: %s", e)
            return None

    def _save_member_hashes_cache(self, hashes: dict[str, str]) -> None:
        """Persist the current member-hash map."""
        try:
            self.check.write_persistent_cache(self.CONSUMER_GROUP_MEMBERS_CACHE_KEY, json.dumps(hashes))
        except Exception as e:
            self.log.debug("Could not write consumer group members cache: %s", e)

    def _build_group_meta_tags(self, state_tags: list[str], group_info) -> list[str]:
        """Build the group-level tag list, appending dimensional metadata when the broker provides it."""
        tags = list(state_tags)
        assignor = getattr(group_info, 'partition_assignor', None)
        # KIP-848 and EMPTY-state groups report an empty assignor; skip it to avoid a blank-value tag.
        if assignor:
            tags.append(f'partition_assignor:{assignor}')
        group_type = getattr(group_info, 'type', None)
        if group_type is not None:
            type_name = group_type.name if hasattr(group_type, 'name') else str(group_type)
            tags.append(f'consumer_group_type:{type_name}')
        is_simple = getattr(group_info, 'is_simple_consumer_group', None)
        if is_simple is not None:
            tags.append(f'is_simple_consumer_group:{str(bool(is_simple)).lower()}')
        return tags

    def _is_group_rebalancing(self, state_name: str, members) -> bool:
        """Detect an in-progress rebalance via group state (classic) or assignment drift (KIP-848)."""
        if state_name in CONSUMER_GROUP_REBALANCING_STATES:
            return True
        for member in members:
            target = getattr(member, 'target_assignment', None)
            if target is None:
                # Classic-protocol member: no KIP-848 target, skip.
                continue
            assignment = getattr(member, 'assignment', None)
            if assignment is None:
                # Member has a target but no current assignment — unambiguous drift.
                return True
            current_tps = {(tp.topic, tp.partition) for tp in assignment.topic_partitions}
            target_tps = {(tp.topic, tp.partition) for tp in target.topic_partitions}
            if current_tps != target_tps:
                return True
        return False

    def _load_schema_id_cache(self) -> dict[str, SchemaDefinition]:
        """Load the permanent schema ID cache from persistent storage.

        Schema IDs in Confluent Schema Registry are immutable: once a schema is
        registered with a given ID, that ID always maps to the same content.
        This cache avoids re-fetching schema content for already-seen IDs.
        """
        try:
            cached_str = self.check.read_persistent_cache(self.SCHEMA_ID_CACHE_KEY)
            return json.loads(cached_str) if cached_str else {}
        except Exception as e:
            self.log.debug("Could not read schema ID cache: %s", e)
            return {}

    def _save_schema_id_cache(self, cache: dict[str, SchemaDefinition]):
        """Persist the schema ID cache, evicting oldest entries if over the size limit."""
        if len(cache) > self.SCHEMA_ID_CACHE_MAX_SIZE:
            # Schema IDs are monotonically increasing, so keep the highest (most recent) ones
            sorted_keys = sorted(cache, key=int)
            for key in sorted_keys[: len(cache) - self.SCHEMA_ID_CACHE_MAX_SIZE]:
                del cache[key]
        try:
            self.check.write_persistent_cache(self.SCHEMA_ID_CACHE_KEY, json.dumps(cache))
        except Exception as e:
            self.log.debug("Could not write schema ID cache: %s", e)

    def _load_latest_version_cache(self) -> dict[str, SubjectVersionInfo]:
        """Load cache mapping subject -> last known max version number."""
        try:
            cached_str = self.check.read_persistent_cache(self.SCHEMA_LATEST_VERSION_CACHE_KEY)
            return json.loads(cached_str) if cached_str else {}
        except Exception as e:
            self.log.debug("Could not read schema latest version cache: %s", e)
            return {}

    def _save_latest_version_cache(self, cache: dict[str, SubjectVersionInfo]):
        """Persist the latest version cache, evicting entries if over the size limit."""
        if len(cache) > self.SCHEMA_ID_CACHE_MAX_SIZE:
            # Evict arbitrary entries; evicted subjects will simply be re-fetched next run
            keys_to_evict = list(cache)[: len(cache) - self.SCHEMA_ID_CACHE_MAX_SIZE]
            for key in keys_to_evict:
                del cache[key]
        try:
            self.check.write_persistent_cache(self.SCHEMA_LATEST_VERSION_CACHE_KEY, json.dumps(cache))
        except Exception as e:
            self.log.debug("Could not write schema latest version cache: %s", e)

    def _load_global_compatibility_cache(self) -> str | None:
        """Return the last successfully fetched global compatibility level."""
        try:
            return self.check.read_persistent_cache(self.GLOBAL_COMPATIBILITY_CACHE_KEY) or None
        except Exception as e:
            self.log.debug("Could not read global compatibility cache: %s", e)
            return None

    def _save_global_compatibility_cache(self, value: str) -> None:
        """Persist the last known global compatibility level."""
        try:
            self.check.write_persistent_cache(self.GLOBAL_COMPATIBILITY_CACHE_KEY, value)
        except Exception as e:
            self.log.debug("Could not write global compatibility cache: %s", e)

    def _collect_schema_registry_info(self, metadata):
        if not self.config._collect_schema_registry:
            return

        self.log.debug("Collecting schema registry information from %s", self.config._collect_schema_registry)

        try:
            self._refresh_schema_registry_oauth_token()
        except Exception as e:
            self.log.error("Failed to refresh Schema Registry OAuth token: %s", e)
            return

        try:
            subjects = self._get_schema_registry_subjects()
        except Exception as e:
            self.log.error("Failed to fetch subjects from Schema Registry: %s", e)
            return

        cluster_id = self.config._kafka_cluster_id_override or (
            metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
        )

        self.log.debug("Found %d subjects in schema registry", len(subjects))

        self.check.gauge('schema_registry.subjects', len(subjects), tags=self.config._get_tags(cluster_id))

        try:
            global_compatibility = self._get_schema_registry_global_compatibility()
            if global_compatibility is not None:
                self._save_global_compatibility_cache(global_compatibility)
            else:
                # A transient empty /config response shouldn't drop global_compatibility from
                # this cycle's payloads — fall back to the last known value, same as the error path.
                global_compatibility = self._load_global_compatibility_cache()
        except Exception as e:
            self.log.warning("Failed to fetch global compatibility from Schema Registry: %s", e)
            global_compatibility = self._load_global_compatibility_cache()

        # --- Tier 1: Lightweight version checks ---
        # GET /subjects/{subject}/versions returns just [1, 2, 3] — very cheap.
        # We use this to detect if a subject has a new version without fetching schema content.
        subjects_to_check = self.cache.get_items_to_fetch(self.SCHEMA_VERSION_CHECK_CACHE_KEY, subjects)

        subjects_to_check = subjects_to_check[: self.SCHEMA_VERSION_CHECK_BATCH_SIZE]

        self.log.debug("Checking versions for %d/%d subjects", len(subjects_to_check), len(subjects))

        # Load the cache of last known max version per subject
        latest_version_cache = self._load_latest_version_cache()

        # Fetch version lists in parallel (lightweight calls)
        version_responses = self._parallel_fetch(self._get_schema_registry_versions, subjects_to_check, "version list")

        # Mark all checked subjects as fetched (even if they errored)
        self.cache.mark_items_fetched(
            self.SCHEMA_VERSION_CHECK_CACHE_KEY,
            subjects_to_check,
            max_cache_size=self.SCHEMA_VERSION_CHECK_CACHE_MAX_SIZE,
        )

        # --- Tier 2: Full fetch only for subjects with new versions ---
        # Compare the max version number to what we've seen before.
        # New subjects (not in cache) also need a full fetch.
        subjects_needing_full_fetch = []
        for subject, versions in version_responses.items():
            if not versions:
                continue
            max_version = max(versions)
            cached = latest_version_cache.get(subject)
            cached_version = cached.get('version', 0) if isinstance(cached, dict) else (cached or 0)
            if max_version > cached_version:
                subjects_needing_full_fetch.append(subject)

        self.log.debug(
            "%d/%d checked subjects have new versions",
            len(subjects_needing_full_fetch),
            len(version_responses),
        )

        # Load permanent schema ID cache — schema IDs are immutable in the registry,
        # so once we have the content for a given ID we never need to fetch it again.
        schema_id_cache = self._load_schema_id_cache()
        schema_id_cache_updated = False

        # Fetch latest versions in parallel for subjects that changed
        schema_responses = self._parallel_fetch(
            self._get_schema_registry_latest_version, subjects_needing_full_fetch, "schema details"
        )

        compatibility_responses = self._collect_subject_compatibilities(subjects, subjects_needing_full_fetch)

        # Apply standalone compatibility updates to existing cache entries so a flip alone (without a
        # version bump) flows into the next schema emission via the cache_content key. This must run
        # before the schema_responses loop below replaces latest_version_cache[subject] for
        # version-bumped subjects; the `subject in schema_responses` guard keeps the two write sites
        # mutually exclusive per subject.
        for subject, compatibility in compatibility_responses.items():
            if compatibility is None or subject in schema_responses:
                continue
            entry = latest_version_cache.get(subject)
            if isinstance(entry, dict):
                entry['compatibility'] = compatibility

        fetched_schemas = {}

        for subject, latest_schema in schema_responses.items():
            schema_id = latest_schema.get('id')
            schema_version = latest_schema.get('version')
            schema_type = latest_schema.get('schemaType', 'AVRO')

            if schema_id is None or schema_version is None:
                self.log.warning("Schema Registry returned incomplete data for %s: %s", subject, latest_schema)
                continue

            # A None here means either the fetch failed or the response carried no
            # compatibilityLevel. With defaultToGlobal=true the registry returns the effective
            # level for any existing subject, so in practice None signals a fetch failure — fall
            # back to the cached value rather than overwriting it with None.
            compatibility = compatibility_responses.get(subject)
            if compatibility is None:
                compatibility = (latest_version_cache.get(subject) or {}).get('compatibility')

            latest_version_cache[subject] = {
                'version': schema_version,
                'schema_id': schema_id,
                'compatibility': compatibility,
            }

            # Use permanent schema ID cache to avoid processing unchanged schemas.
            schema_id_str = str(schema_id)
            cached_entry = schema_id_cache.get(schema_id_str)
            if cached_entry:
                schema_content = cached_entry['schema']
                schema_type = cached_entry.get('schema_type', schema_type)
            else:
                schema_content = latest_schema.get('schema', '')
                schema_id_cache[schema_id_str] = {
                    'schema': schema_content,
                    'schema_type': schema_type,
                }
                schema_id_cache_updated = True

            cache_content = f"{schema_id}:{schema_version}:{compatibility}:{global_compatibility}:{schema_content}"

            fetched_schemas[subject] = {
                'cache_content': cache_content,
                **self._build_schema_info(
                    subject, schema_content, schema_type, schema_version, schema_id, compatibility
                ),
            }

        # Persist caches
        self._save_latest_version_cache(latest_version_cache)
        if schema_id_cache_updated:
            self._save_schema_id_cache(schema_id_cache)

        # Build lightweight cache_content strings for all known subjects (from cache, no extra HTTP calls).
        # This allows re-emission of unchanged schemas when the event cache TTL expires.
        # Note: changing the cache_content format (e.g. adding the compatibility fields) makes every
        # cached subject hash differently on the first run after an upgrade, so all known schemas
        # re-emit once. This is self-healing and bounded to a single collection cycle.
        all_schema_cache_contents = {subject: info['cache_content'] for subject, info in fetched_schemas.items()}
        for subject in subjects:
            if subject in all_schema_cache_contents:
                continue

            cached_info = latest_version_cache.get(subject)
            if not isinstance(cached_info, dict):
                continue

            version = cached_info.get('version')
            schema_id = cached_info.get('schema_id')
            if version is None or schema_id is None:
                continue

            schema_id_str = str(schema_id)
            id_entry = schema_id_cache.get(schema_id_str)
            if not id_entry:
                continue

            cached_compat = cached_info.get('compatibility')
            all_schema_cache_contents[subject] = (
                f"{schema_id}:{version}:{cached_compat}:{global_compatibility}:{id_entry['schema']}"
            )

        # Determine which subjects need event emission (changed or TTL expired)
        schemas_to_emit = self.cache.get_events_to_send(self.SCHEMA_CACHE_KEY, all_schema_cache_contents)

        self._emit_schema_registry_events(
            schemas_to_emit,
            fetched_schemas,
            latest_version_cache,
            schema_id_cache,
            cluster_id,
            global_compatibility,
        )

    def _collect_subject_compatibilities(
        self,
        subjects: list[str],
        subjects_needing_full_fetch: list[str],
    ) -> dict[str, str | None]:
        """Fetch per-subject compatibility on a cadence and return the raw results.

        Compatibility is refreshed on its own cadence so a flip without a version bump is still picked
        up; a per-subject flip therefore surfaces only on the next compat-fetch cadence (up to
        cache.refresh_interval + jitter later), while a global flip re-emits immediately via
        global_compatibility.

        The SCHEMA_COMPATIBILITY_BATCH_SIZE clamp bounds only the cadence-driven `compat_due` list;
        version-bumped subjects are always fetched on top of that budget, so the effective ceiling on
        /config/{subject} calls is SCHEMA_VERSION_CHECK_BATCH_SIZE (which bounds
        subjects_needing_full_fetch), not SCHEMA_COMPATIBILITY_BATCH_SIZE. They are equal today, so
        there is no over-fetch.
        """
        compat_due = self.cache.get_items_to_fetch(self.SCHEMA_COMPATIBILITY_FETCH_CACHE_KEY, subjects)
        remaining_slots = max(0, self.SCHEMA_COMPATIBILITY_BATCH_SIZE - len(subjects_needing_full_fetch))
        compat_due = compat_due[:remaining_slots]
        compat_subjects_to_fetch = list(set(subjects_needing_full_fetch) | set(compat_due))

        compatibility_responses: dict[str, str | None] = self._parallel_fetch(
            self._get_schema_registry_subject_compatibility, compat_subjects_to_fetch, "compatibility"
        )
        if compat_subjects_to_fetch:
            # Mark all attempted subjects as fetched (even if they errored), mirroring the version
            # tier: a subject that fails this run isn't retried until the next configs cadence rather
            # than hammered every check, at the cost of holding stale compatibility until then.
            self.cache.mark_items_fetched(
                self.SCHEMA_COMPATIBILITY_FETCH_CACHE_KEY,
                compat_subjects_to_fetch,
                ttl_base=self.cache.refresh_interval,
                ttl_jitter=self.cache.refresh_jitter,
                max_cache_size=self.SCHEMA_COMPATIBILITY_FETCH_CACHE_MAX_SIZE,
            )

        return compatibility_responses

    def _build_schema_info(
        self,
        subject: str,
        schema_content: str,
        schema_type: str,
        schema_version: int | None,
        schema_id: int | None,
        compatibility: str | None,
    ) -> SchemaInfo:
        """Assemble the canonical schema info dict used to build a data-streams schema payload."""
        topic_name, schema_for = self._parse_subject(subject)
        return {
            'schema_content': schema_content,
            'topic_name': topic_name,
            'schema_for': schema_for,
            'schema_version': schema_version,
            'schema_id': schema_id,
            'schema_type': schema_type,
            'compatibility': compatibility,
        }

    def _emit_schema_registry_events(
        self,
        subjects_to_emit: list[str],
        fetched_schemas: dict[str, dict],
        latest_version_cache: dict[str, SubjectVersionInfo],
        schema_id_cache: dict[str, SchemaDefinition],
        cluster_id: str,
        global_compatibility: str | None,
    ):
        """Emit a data-streams-message payload for each subject that changed or whose event TTL expired."""
        for subject in subjects_to_emit:
            if subject in fetched_schemas:
                info = fetched_schemas[subject]
            else:
                cached_info = latest_version_cache.get(subject, {})
                schema_id = cached_info.get('schema_id')
                id_entry = schema_id_cache.get(str(schema_id), {})
                info = self._build_schema_info(
                    subject,
                    id_entry.get('schema', ''),
                    id_entry.get('schema_type', 'AVRO'),
                    cached_info.get('version'),
                    schema_id,
                    cached_info.get('compatibility'),
                )

            ds_payload = {
                'collection_timestamp': int(time.time() * 1000),
                'kafka_cluster_id': cluster_id,
                **self.config._original_cluster_id_field(),
                'subject': subject,
                'topic': info['topic_name'],
                'schema_for': info['schema_for'],
                'schema_id': info['schema_id'],
                'schema_version': info['schema_version'],
                'schema_type': info['schema_type'],
                'config_type': 'schema',
                'schema': info['schema_content'],
            }
            subject_compat = info.get('compatibility')
            if subject_compat is not None:
                ds_payload['compatibility'] = subject_compat
            if global_compatibility is not None:
                ds_payload['global_compatibility'] = global_compatibility

            self.check.event_platform_event(json.dumps(ds_payload), "data-streams-message")

    @staticmethod
    def _parse_subject(subject: str) -> tuple[str, str]:
        """Extract topic name and schema type (key/value) from a Schema Registry subject name."""
        if subject.endswith('-value'):
            return subject.removesuffix('-value'), 'value'
        if subject.endswith('-key'):
            return subject.removesuffix('-key'), 'key'
        return subject, 'unknown'

    def _truncate_config_for_event(self, config_data, max_configs=50):
        """
        Truncate broker/topic configs to avoid event size limits.
        Always keeps important configs, then fills remaining space with others.
        Returns a sorted dict for stable caching and comparison.

        Args:
            config_data: Dict of config key-value pairs
            max_configs: Maximum number of configs to include (default 50)

        Returns:
            Sorted dict with most important configs (deterministic output)
        """
        # Important configs that should always be included (order doesn't matter, will be sorted)
        important_broker_configs = {
            # Replication & durability
            'default.replication.factor',
            'min.insync.replicas',
            'unclean.leader.election.enable',
            # Retention
            'log.retention.bytes',
            'log.retention.ms',
            'log.retention.hours',
            'log.segment.bytes',
            # Performance
            'num.io.threads',
            'num.network.threads',
            'num.partitions',
            'num.replica.fetchers',
            'socket.send.buffer.bytes',
            'socket.receive.buffer.bytes',
            'replica.fetch.max.bytes',
            # Broker identity
            'broker.id',
            'broker.rack',
            'listeners',
            'advertised.listeners',
            # Cluster coordination
            'zookeeper.connect',
            'controller.quorum.voters',
            'inter.broker.protocol.version',
            # Compression
            'compression.type',
            # Topic management
            'auto.create.topics.enable',
            'delete.topic.enable',
            # Security
            'authorizer.class.name',
            'security.inter.broker.protocol',
            # Log cleanup
            'log.cleanup.policy',
            'log.cleaner.enable',
        }

        important_found = {}
        remaining = {}

        for key, value in config_data.items():
            if key in important_broker_configs:
                important_found[key] = value
            else:
                remaining[key] = value

        # Start with all important configs (sorted)
        selected_configs = []
        for key in sorted(important_found.keys()):
            selected_configs.append((key, important_found[key]))

        # Add remaining configs (sorted) until we hit the limit
        for key in sorted(remaining.keys()):
            if len(selected_configs) >= max_configs:
                break
            selected_configs.append((key, remaining[key]))

        return dict(selected_configs)

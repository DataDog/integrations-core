# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Kafka Cluster Metadata Collection."""

import hashlib
import json
import time

from confluent_kafka.admin import ConfigResource, ResourceType

from datadog_checks.kafka_consumer.constants import KAFKA_INTERNAL_TOPICS, LOW_WATERMARK


class ClusterMetadataCollector:
    """Collects Kafka cluster metadata (brokers, topics, consumer groups, schemas)."""

    def __init__(self, check, client, config, log):
        self.check = check
        self.client = client
        self.config = config
        self.log = log
        self.http = check.http

        self.EVENT_CACHE_TTL = 600  # 10 minutes in seconds

        self.BROKER_CONFIG_CACHE_KEY = 'kafka_broker_config_cache'
        self.TOPIC_CONFIG_CACHE_KEY = 'kafka_topic_config_cache'
        self.SCHEMA_CACHE_KEY = 'kafka_schema_cache'
        self.TOPIC_HWM_SUM_CACHE_KEY = 'kafka_topic_hwm_sum_cache'

        if self.config._collect_schema_registry:
            self._configure_schema_registry_http_client()

    def _configure_schema_registry_http_client(self):
        """Configure the HTTP client with authentication and TLS settings for Schema Registry."""
        if self.config._schema_registry_username and self.config._schema_registry_password:
            self.log.debug("Configuring Schema Registry with Basic Authentication")
            self.http.options['auth'] = (
                self.config._schema_registry_username,
                self.config._schema_registry_password,
            )

        if not self.config._schema_registry_tls_verify:
            self.log.debug("Schema Registry TLS verification is disabled")
            self.http.options['verify'] = False
        elif self.config._schema_registry_tls_ca_cert:
            self.log.debug("Using custom CA certificate for Schema Registry")
            self.http.options['verify'] = self.config._schema_registry_tls_ca_cert
        else:
            self.http.options['verify'] = True

        if self.config._schema_registry_tls_cert and self.config._schema_registry_tls_key:
            self.log.debug("Configuring Schema Registry with client certificate authentication")
            self.http.options['cert'] = (
                self.config._schema_registry_tls_cert,
                self.config._schema_registry_tls_key,
            )
        elif self.config._schema_registry_tls_cert:
            self.http.options['cert'] = self.config._schema_registry_tls_cert

    def _get_schema_registry_subjects(self):
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/subjects")
        response.raise_for_status()
        return response.json()

    def _get_schema_registry_versions(self, subject):
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/subjects/{subject}/versions")
        response.raise_for_status()
        return response.json()

    def _get_schema_registry_latest_version(self, subject):
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/subjects/{subject}/versions/latest")
        response.raise_for_status()
        return response.json()

    def collect_all_metadata(self, highwater_offsets):
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
            self._collect_topic_metadata(shared_metadata, highwater_offsets)
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

    def _should_emit_cached_event(self, cache_key_prefix: str, item_key: str, content: str) -> bool:
        current_time = time.time()
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

        try:
            cached_data_str = self.check.read_persistent_cache(cache_key_prefix)
            if cached_data_str:
                cache_dict = json.loads(cached_data_str)
            else:
                cache_dict = {}
        except Exception as e:
            self.log.debug("Could not read event cache: %s", e)
            cache_dict = {}

        if item_key not in cache_dict:
            cache_dict[item_key] = {'hash': content_hash, 'last_emit': current_time}
            self._write_cache(cache_key_prefix, cache_dict)
            return True

        cached_entry = cache_dict[item_key]

        if 'hash' not in cached_entry or cached_entry.get('hash') != content_hash:
            cache_dict[item_key] = {'hash': content_hash, 'last_emit': current_time}
            self._write_cache(cache_key_prefix, cache_dict)
            return True

        if current_time - cached_entry.get('last_emit', 0) >= self.EVENT_CACHE_TTL:
            cached_entry['last_emit'] = current_time
            cache_dict[item_key] = cached_entry
            self._write_cache(cache_key_prefix, cache_dict)
            return True

        return False

    def _write_cache(self, cache_key: str, cache_dict: dict):
        try:
            self.check.write_persistent_cache(cache_key, json.dumps(cache_dict))
        except Exception as e:
            self.log.warning("Could not write event cache: %s", e)

    def _collect_broker_metadata(self, metadata=None):
        self.log.debug("Collecting broker metadata")

        if metadata is None:
            try:
                metadata = self.client.kafka_client.list_topics(timeout=self.config._request_timeout)
            except Exception as e:
                self.log.debug("Could not list topics for broker metadata: %s", e)
                return

        brokers = metadata.brokers
        cluster_id = metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'

        self.log.debug("Found %s brokers in cluster %s", len(brokers), cluster_id)
        broker_tags = self._get_tags(cluster_id) + [f'bootstrap_servers:{self.config._kafka_connect_str}']
        self.check.gauge('broker.count', len(brokers), tags=broker_tags)

        try:
            cluster_future = self.client.kafka_client.describe_cluster()
            cluster_info = cluster_future.result(timeout=self.config._request_timeout)

            if cluster_info.controller:
                controller_tags = self._get_tags(cluster_id) + [
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

        for broker_id, broker_metadata in brokers.items():
            broker_host = broker_metadata.host
            broker_port = broker_metadata.port

            tags = self._get_tags(cluster_id) + [
                f'broker_id:{broker_id}',
                f'broker_host:{broker_host}',
                f'broker_port:{broker_port}',
            ]

            self.check.gauge('broker.leader_count', broker_leader_count.get(broker_id, 0), tags=tags)
            self.check.gauge('broker.partition_count', broker_partition_count.get(broker_id, 0), tags=tags)

            try:
                resources = [ConfigResource(ResourceType.BROKER, str(broker_id))]
                futures = self.client.kafka_client.describe_configs(resources)

                for _resource, future in futures.items():
                    config_entries = future.result(timeout=self.config._request_timeout)

                    config_data = {}
                    for config_name, config_entry in config_entries.items():
                        config_data[config_name] = config_entry.value

                        if config_name in [
                            'log.retention.bytes',
                            'log.retention.ms',
                            'log.segment.bytes',
                            'num.partitions',
                            'num.network.threads',
                            'num.io.threads',
                            'default.replication.factor',
                            'min.insync.replicas',
                        ]:
                            try:
                                value = float(config_entry.value) if config_entry.value else 0
                                metric_name = f"broker.config.{config_name.replace('.', '_')}"
                                self.check.gauge(metric_name, value, tags=tags)
                            except (ValueError, TypeError):
                                pass

                    truncated_config = self._truncate_config_for_event(config_data, max_configs=50)

                    event_text = json.dumps(truncated_config, indent=2, sort_keys=True)

                    if self._should_emit_cached_event(self.BROKER_CONFIG_CACHE_KEY, str(broker_id), event_text):
                        self.check.event(
                            {
                                'timestamp': int(time.time()),
                                'event_type': 'config_change',
                                'source_type_name': 'kafka',
                                'msg_title': f'Broker {broker_id} Configuration',
                                'msg_text': event_text,
                                'tags': tags + ['event_type:broker_config'],
                                'aggregation_key': f'kafka_broker_config_{broker_id}',
                                'alert_type': 'info',
                            }
                        )

            except Exception as e:
                self.log.warning("Failed to describe configs for broker %s: %s", broker_id, e)

    def _collect_topic_metadata(self, metadata, highwater_offsets):
        self.log.debug("Collecting topic metadata")

        topic_partitions = self.client.get_topic_partitions()

        cluster_id = metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
        all_topics_metadata = metadata.topics

        self.log.debug("Found %s topics", len(topic_partitions))

        self.check.gauge('topic.count', len(topic_partitions), tags=self._get_tags(cluster_id))

        earliest_offsets, _ = self.check.get_watermark_offsets(None, mode=LOW_WATERMARK)

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

            topic_tags = self._get_tags(cluster_id) + [f'topic:{topic_name}']

            if not partitions:
                self.log.warning("No partitions found for topic %s", topic_name)
                continue

            self.check.gauge('topic.partitions', len(partitions), tags=topic_tags)

            total_messages = 0
            topic_metadata = all_topics_metadata.get(topic_name)

            if not topic_metadata:
                self.log.warning("No metadata found for topic %s", topic_name)
                continue

            for partition_id in partitions:
                partition_tags = topic_tags + [f'partition:{partition_id}']

                partition_metadata = topic_metadata.partitions.get(partition_id)
                latest = highwater_offsets.get((topic_name, partition_id), 0)
                earliest = earliest_offsets.get((topic_name, partition_id), 0)
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

                    self.check.gauge('partition.replicas', len(replicas), tags=partition_broker_tags)
                    self.check.gauge('partition.isr', len(isrs), tags=partition_broker_tags)

                    self.check.gauge('partition.size', partition_size, tags=partition_broker_tags)

                    is_under_replicated = len(isrs) < len(replicas)
                    self.check.gauge(
                        'partition.under_replicated',
                        1 if is_under_replicated else 0,
                        tags=partition_broker_tags,
                    )

                    is_offline = leader == -1
                    self.check.gauge('partition.offline', 1 if is_offline else 0, tags=partition_broker_tags)
                else:
                    self.check.gauge('partition.size', partition_size, tags=partition_tags)

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

            resources = [ConfigResource(ResourceType.TOPIC, topic_name)]
            futures = self.client.kafka_client.describe_configs(resources)
            config_result = futures[resources[0]].result(timeout=self.config._request_timeout)

            if not config_result:
                continue

            topic_config = {}
            for config_name, config_entry in config_result.items():
                topic_config[config_name] = config_entry.value

            if topic_config:
                truncated_config = self._truncate_config_for_event(topic_config, max_configs=30)

                event_text = json.dumps(truncated_config, indent=2, sort_keys=True)

                if self._should_emit_cached_event(self.TOPIC_CONFIG_CACHE_KEY, topic_name, event_text):
                    self.check.event(
                        {
                            'timestamp': int(time.time()),
                            'event_type': 'info',
                            'source_type_name': 'kafka',
                            'msg_title': f'Topic: {topic_name} (custom config)',
                            'msg_text': event_text,
                            'tags': topic_tags + ['event_type:topic_config'],
                            'aggregation_key': f'kafka_topic_config_{topic_name}',
                            'alert_type': 'info',
                        }
                    )

                if 'retention.ms' in topic_config and topic_config['retention.ms'] != '-1':
                    retention_ms = int(topic_config['retention.ms'])
                    self.check.gauge('topic.config.retention_ms', retention_ms, tags=topic_tags)

                if 'retention.bytes' in topic_config and topic_config['retention.bytes'] != '-1':
                    retention_bytes = int(topic_config['retention.bytes'])
                    self.check.gauge('topic.config.retention_bytes', retention_bytes, tags=topic_tags)

                if 'max.message.bytes' in topic_config:
                    max_bytes = int(topic_config['max.message.bytes'])
                    self.check.gauge('topic.config.max_message_bytes', max_bytes, tags=topic_tags)

        try:
            snapshot = {'ts': float(now_ts), 'partitions': current_partition_offsets}
            self.check.write_persistent_cache(self.TOPIC_HWM_SUM_CACHE_KEY, json.dumps(snapshot))
        except Exception as e:
            self.log.debug("Could not write topic HWM cache: %s", e)

    def _collect_consumer_group_metadata(self, metadata):
        self.log.debug("Collecting consumer group metadata")
        cluster_id = metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
        consumer_groups_future = self.client.kafka_client.list_consumer_groups()
        consumer_groups_result = consumer_groups_future.result(timeout=self.config._request_timeout)

        if consumer_groups_result.errors:
            self.log.warning("Errors listing consumer groups: %s", consumer_groups_result.errors)

        consumer_groups = consumer_groups_result.valid

        self.log.debug("Found %s consumer groups", len(consumer_groups))
        self.check.gauge('consumer_group.count', len(consumer_groups), tags=self._get_tags(cluster_id))

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

        for group_id, group_info in group_id_to_info.items():
            group_tags = self._get_tags(cluster_id) + [f'consumer_group:{group_id}']
            state = group_info.state
            members = group_info.members
            coordinator = group_info.coordinator
            state_name = state.name if hasattr(state, 'name') else str(state)
            state_tags = group_tags + [f'consumer_group_state:{state_name}']
            if coordinator:
                state_tags.append(f'coordinator:{coordinator.id}')

            self.check.gauge('consumer_group.members', len(members), tags=state_tags)

            member_info = []
            topics_for_group = set()

            for member in members:
                member_id = member.member_id
                client_id = member.client_id
                host = member.host

                member_info.append({'member_id': member_id, 'client_id': client_id, 'host': host})

                if hasattr(member, 'assignment') and member.assignment:
                    partition_count = len(member.assignment.topic_partitions)

                    member_tags = state_tags + [
                        f'client_id:{client_id}',
                        f'member_host:{host}',
                    ]
                    self.check.gauge('consumer_group.member.partitions', partition_count, tags=member_tags)

                    for tp in member.assignment.topic_partitions:
                        topics_for_group.add(tp.topic)

    def _collect_schema_registry_info(self, metadata):
        if not self.config._collect_schema_registry:
            return

        self.log.debug("Collecting schema registry information from %s", self.config._collect_schema_registry)

        try:
            subjects = self._get_schema_registry_subjects()
        except Exception as e:
            self.log.error("Failed to fetch subjects from Schema Registry: %s", e)
            return

        cluster_id = metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'

        self.log.debug("Found %s schemas in schema registry", len(subjects))

        self.check.gauge('schema_registry.subjects', len(subjects), tags=self._get_tags(cluster_id))

        for subject in subjects:
            subject_tags = self._get_tags(cluster_id) + [f'subject:{subject}']

            try:
                versions = self._get_schema_registry_versions(subject)

                self.check.gauge('schema_registry.versions', len(versions), tags=subject_tags)

                latest_schema = self._get_schema_registry_latest_version(subject)

                schema_id = latest_schema.get('id')
                schema_version = latest_schema.get('version')
                schema_type = latest_schema.get('schemaType', 'AVRO')
                schema_content = latest_schema.get('schema', '')

                # Extract topic name and schema type (key/value) from subject
                # Subjects follow patterns: "topic-key", "topic-value"
                topic_name = subject
                schema_for = 'unknown'

                if subject.endswith('-value'):
                    topic_name = subject[:-6]  # Remove '-value'
                    schema_for = 'value'
                elif subject.endswith('-key'):
                    topic_name = subject[:-4]  # Remove '-key'
                    schema_for = 'key'

                event_tags = subject_tags + [
                    f'schema_id:{schema_id}',
                    f'schema_version:{schema_version}',
                    f'schema_type:{schema_type}',
                    f'topic:{topic_name}',
                    f'schema_for:{schema_for}',
                    'event_type:schema_registry',
                ]

                cache_content = f"{schema_id}:{schema_version}:{schema_content}"

                if self._should_emit_cached_event(self.SCHEMA_CACHE_KEY, subject, cache_content):
                    self.check.event(
                        {
                            'timestamp': int(time.time()),
                            'event_type': 'info',
                            'source_type_name': 'kafka',
                            'msg_title': f'{topic_name} ({schema_for}) - Schema v{schema_version}',
                            'msg_text': schema_content,
                            'tags': event_tags,
                            'aggregation_key': f'kafka_schema_{subject}_{schema_version}',
                            'alert_type': 'info',
                        }
                    )

            except Exception as e:
                self.log.warning("Error getting schema details for %s: %s", subject, e)

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

    def _get_tags(self, cluster_id: str | None = None) -> list[str]:
        tags = list(self.config._custom_tags)
        if cluster_id:
            tags.append(f'kafka_cluster_id:{cluster_id}')
        return tags

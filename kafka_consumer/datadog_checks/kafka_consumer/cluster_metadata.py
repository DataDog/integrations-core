# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
Kafka Cluster Metadata Collection Module

This module extends the kafka_consumer check to collect comprehensive cluster metadata including:
- Broker configurations
- Topic and partition metadata (sizes, offsets, replication info)
- Consumer group details (members, state, topics)
- Schema Registry information
"""

import json
import time


class ClusterMetadataCollector:
    """
    Collects comprehensive Kafka cluster metadata.
    
    This collector works alongside the existing kafka_consumer check to provide
    additional insights about the Kafka cluster topology and configuration.
    """
    
    def __init__(self, check, client, config, log):
        """
        Initialize the cluster metadata collector.
        
        Args:
            check: The parent KafkaCheck instance (for submitting metrics/events)
            client: The KafkaClient instance
            config: The KafkaConfig instance
            log: Logger instance
        """
        self.check = check
        self.client = client
        self.config = config
        self.log = log
        
    def collect_all_metadata(self):
        """Collect all cluster metadata based on configuration."""
        try:
            # Collect broker information
            if self.config._collect_broker_metadata:
                self._collect_broker_metadata()
            
            # Collect topic metadata  
            if self.config._collect_topic_metadata:
                self._collect_topic_metadata()
            
            # Collect consumer group metadata
            if self.config._collect_consumer_group_metadata:
                self._collect_consumer_group_metadata()
            
            # Collect schema registry information
            if self.config._collect_schema_registry:
                self._collect_schema_registry_info()
                
        except Exception as e:
            self.log.error(f"Error collecting cluster metadata: {e}")
    
    def _collect_broker_metadata(self):
        """Collect broker configuration and information."""
        try:
            from confluent_kafka.admin import ConfigResource, ResourceType
            
            self.log.info("Collecting broker metadata")
            
            # Get cluster metadata to get cluster_id
            metadata = self.client.kafka_client.list_topics(timeout=self.config._request_timeout)
            brokers = metadata.brokers
            cluster_id = metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
            
            self.log.info(f"Found {len(brokers)} brokers in cluster {cluster_id}")
            
            # Emit metric for number of brokers
            broker_tags = self._get_tags(cluster_id)
            self.check.gauge('broker.count', len(brokers), tags=broker_tags)
            
            # Track leader count and partition distribution per broker
            broker_leader_count = {broker_id: 0 for broker_id in brokers.keys()}
            broker_partition_count = {broker_id: 0 for broker_id in brokers.keys()}
            
            # Count leaders and partitions per broker from metadata
            for topic_name, topic_metadata in metadata.topics.items():
                if topic_name.startswith('__'):
                    continue
                for partition_id, partition_metadata in topic_metadata.partitions.items():
                    if partition_metadata.leader in broker_leader_count:
                        broker_leader_count[partition_metadata.leader] += 1
                    for replica in partition_metadata.replicas:
                        if replica in broker_partition_count:
                            broker_partition_count[replica] += 1
            
            # Get configuration for each broker
            for broker_id, broker_metadata in brokers.items():
                broker_host = broker_metadata.host
                broker_port = broker_metadata.port
                
                tags = self._get_tags(cluster_id) + [
                    f'broker_id:{broker_id}',
                    f'broker_host:{broker_host}',
                    f'broker_port:{broker_port}'
                ]
                
                # Emit broker-specific metrics
                self.check.gauge('broker.leader_count', broker_leader_count.get(broker_id, 0), tags=tags)
                self.check.gauge('broker.partition_count', broker_partition_count.get(broker_id, 0), tags=tags)
                
                try:
                    # Get broker configuration
                    resources = [ConfigResource(ResourceType.BROKER, str(broker_id))]
                    futures = self.client.kafka_client.describe_configs(resources)
                    
                    # Wait for the result
                    for resource, future in futures.items():
                        try:
                            config_entries = future.result(timeout=self.config._request_timeout / 1000)
                            
                            # Extract important configuration values
                            important_configs = [
                                'advertised.listeners',
                                'auto.create.topics.enable',
                                'log.dirs',
                                'log.retention.bytes',
                                'log.retention.ms',
                                'log.segment.bytes',
                                'num.partitions',
                                'num.network.threads',
                                'num.io.threads',
                                'default.replication.factor',
                                'min.insync.replicas',
                            ]
                            
                            config_data = {}
                            for config_name, config_entry in config_entries.items():
                                if config_name in important_configs:
                                    config_data[config_name] = config_entry.value
                                    
                                    # Emit metrics for numeric configs
                                    if config_name in ['log.retention.bytes', 'log.retention.ms', 
                                                       'log.segment.bytes', 'num.partitions',
                                                       'num.network.threads', 'num.io.threads',
                                                       'default.replication.factor', 'min.insync.replicas']:
                                        try:
                                            value = float(config_entry.value) if config_entry.value else 0
                                            metric_name = f"broker.config.{config_name.replace('.', '_')}"
                                            self.check.gauge(metric_name, value, tags=tags)
                                        except (ValueError, TypeError):
                                            pass
                            
                            # Send configuration as an event in JSON format
                            event_text = json.dumps(config_data, indent=2, sort_keys=True)
                            
                            self.check.event({
                                'timestamp': int(time.time()),
                                'event_type': 'config_change',
                                'source_type_name': 'kafka',
                                'msg_title': f'Broker {broker_id} Configuration',
                                'msg_text': event_text,
                                'tags': tags + ['event_type:broker_config'],
                                'aggregation_key': f'kafka_broker_config_{broker_id}',
                                'alert_type': 'info'
                            })
                            
                        except Exception as e:
                            self.log.warning(f"Failed to get config result for broker {broker_id}: {e}")
                            
                except Exception as e:
                    self.log.warning(f"Failed to describe configs for broker {broker_id}: {e}")
                    
        except Exception as e:
            self.log.error(f"Error collecting broker metadata: {e}")
    
    def _collect_topic_metadata(self):
        """Collect detailed information about topics and partitions."""
        try:
            self.log.info("Collecting topic metadata")
            
            # Get all topics
            topic_partitions = self.client.get_topic_partitions()
            
            # Get cluster_id
            metadata = self.client.kafka_client.list_topics(timeout=self.config._request_timeout)
            cluster_id = metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
            
            self.log.info(f"Found {len(topic_partitions)} topics")
            
            # Emit metric for total number of topics
            self.check.gauge('topic.count', len(topic_partitions), tags=self._get_tags(cluster_id))
            
            # Open a consumer to query offsets
            consumer_group = "datadog-agent-metadata"
            self.client.open_consumer(consumer_group)
            
            try:
                # Iterate through each topic
                for topic_name, partitions in topic_partitions.items():
                    # Skip internal topics if not configured to monitor them
                    if topic_name.startswith('__') and not self.config._monitor_unlisted_consumer_groups:
                        continue
                    
                    topic_tags = self._get_tags(cluster_id) + [f'topic:{topic_name}']
                    
                    try:
                        if not partitions:
                            self.log.warning(f"No partitions found for topic {topic_name}")
                            continue
                        
                        # Emit metric for number of partitions
                        self.check.gauge('topic.partitions', len(partitions), tags=topic_tags)
                        
                        # Track topic size metrics
                        total_messages = 0
                        
                        # Get metadata for detailed partition info
                        metadata = self.client.kafka_client.list_topics(topic_name, timeout=self.config._request_timeout)
                        topic_metadata = metadata.topics.get(topic_name)
                        
                        if not topic_metadata:
                            continue
                        
                        # Iterate through each partition
                        for partition_id in partitions:
                            partition_tags = topic_tags + [f'partition:{partition_id}']
                            
                            try:
                                from confluent_kafka import TopicPartition
                                
                                # Create TopicPartition object
                                tp = TopicPartition(topic_name, partition_id)
                                
                                # Get low and high watermarks
                                low_offset, high_offset = self.client._consumer.get_watermark_offsets(
                                    tp, 
                                    timeout=self.config._request_timeout / 1000
                                )
                                
                                # Calculate partition size (number of messages)
                                partition_size = high_offset - low_offset
                                total_messages += partition_size
                                
                                # Emit partition metrics
                                self.check.gauge('partition.beginning_offset', low_offset, tags=partition_tags)
                                self.check.gauge('partition.end_offset', high_offset, tags=partition_tags)
                                self.check.gauge('partition.size', partition_size, tags=partition_tags)
                                
                                # Get partition metadata (leader, replicas, ISRs)
                                partition_metadata = topic_metadata.partitions.get(partition_id)
                                if partition_metadata:
                                    leader = partition_metadata.leader
                                    replicas = partition_metadata.replicas
                                    isrs = partition_metadata.isrs
                                    
                                    partition_leader_tags = partition_tags + [f'leader:{leader}']
                                    
                                    self.check.gauge('partition.replicas', len(replicas), tags=partition_leader_tags)
                                    self.check.gauge('partition.isr', len(isrs), tags=partition_leader_tags)
                                    
                                    # Check if partition is under-replicated
                                    is_under_replicated = len(isrs) < len(replicas)
                                    self.check.gauge('partition.under_replicated', 
                                                   1 if is_under_replicated else 0, 
                                                   tags=partition_leader_tags)
                                    
                                    # Check if partition has a leader
                                    is_offline = leader == -1
                                    self.check.gauge('partition.offline',
                                                   1 if is_offline else 0,
                                                   tags=partition_tags)
                                
                            except Exception as e:
                                self.log.warning(f"Error collecting metadata for partition {topic_name}:{partition_id}: {e}")
                        
                        # Emit total topic size
                        self.check.gauge('topic.size', total_messages, tags=topic_tags)
                        
                        # Calculate message rate (requires caching previous values)
                        cache_key = f"topic_size_{topic_name}"
                        current_time = time.time()
                        
                        if hasattr(self, '_topic_size_cache'):
                            if cache_key in self._topic_size_cache:
                                prev_size, prev_time = self._topic_size_cache[cache_key]
                                time_diff = current_time - prev_time
                                if time_diff > 0:
                                    message_rate = (total_messages - prev_size) / time_diff
                                    self.check.gauge('topic.message_rate', message_rate, tags=topic_tags)
                        else:
                            self._topic_size_cache = {}
                        
                        self._topic_size_cache[cache_key] = (total_messages, current_time)
                        
                        # Collect topic-level configuration
                        try:
                            from confluent_kafka.admin import ConfigResource, ResourceType
                            
                            resources = [ConfigResource(ResourceType.TOPIC, topic_name)]
                            futures = self.client.kafka_client.describe_configs(resources)
                            
                            for resource, future in futures.items():
                                try:
                                    config_result = future.result(timeout=self.config._request_timeout / 1000)
                                    
                                    if config_result:
                                        # Extract relevant topic configs
                                        topic_config = {}
                                        important_configs = [
                                            'retention.ms', 'retention.bytes', 'segment.ms', 'segment.bytes',
                                            'cleanup.policy', 'compression.type', 'min.insync.replicas',
                                            'max.message.bytes', 'min.compaction.lag.ms', 'delete.retention.ms'
                                        ]
                                        
                                        for config_name, config_entry in config_result.items():
                                            if config_name in important_configs:
                                                # Only include if it's explicitly set (not default)
                                                if not config_entry.is_default:
                                                    topic_config[config_name] = config_entry.value
                                        
                                        # Only emit event if topic has custom configs
                                        if topic_config:
                                            # Build event text in JSON format
                                            event_text = json.dumps(topic_config, indent=2, sort_keys=True)
                                            
                                            # Emit event with topic config
                                            self.check.event({
                                                'timestamp': int(time.time()),
                                                'event_type': 'info',
                                                'source_type_name': 'kafka',
                                                'msg_title': f'Topic: {topic_name} (custom config)',
                                                'msg_text': event_text,
                                                'tags': topic_tags + ['event_type:topic_config'],
                                                'aggregation_key': f'kafka_topic_config_{topic_name}',
                                                'alert_type': 'info'
                                            })
                                            
                                            # Emit metrics for numeric configs
                                            if 'retention.ms' in topic_config and topic_config['retention.ms'] != '-1':
                                                try:
                                                    retention_ms = int(topic_config['retention.ms'])
                                                    self.check.gauge('topic.config.retention_ms', retention_ms, tags=topic_tags)
                                                except (ValueError, TypeError):
                                                    pass
                                            
                                            if 'retention.bytes' in topic_config and topic_config['retention.bytes'] != '-1':
                                                try:
                                                    retention_bytes = int(topic_config['retention.bytes'])
                                                    self.check.gauge('topic.config.retention_bytes', retention_bytes, tags=topic_tags)
                                                except (ValueError, TypeError):
                                                    pass
                                            
                                            if 'max.message.bytes' in topic_config:
                                                try:
                                                    max_bytes = int(topic_config['max.message.bytes'])
                                                    self.check.gauge('topic.config.max_message_bytes', max_bytes, tags=topic_tags)
                                                except (ValueError, TypeError):
                                                    pass
                                        
                                except Exception as e:
                                    self.log.warning(f"Failed to get config result for topic {topic_name}: {e}")
                        
                        except Exception as e:
                            self.log.warning(f"Failed to describe configs for topic {topic_name}: {e}")
                        
                    except Exception as e:
                        self.log.error(f"Error processing topic {topic_name}: {e}")
                        
            finally:
                self.client.close_consumer()
                    
        except Exception as e:
            self.log.error(f"Error collecting topic metadata: {e}")
    
    def _collect_consumer_group_metadata(self):
        """Collect detailed information about consumer groups."""
        try:
            self.log.info("Collecting consumer group metadata")
            
            # Get cluster_id
            metadata = self.client.kafka_client.list_topics(timeout=self.config._request_timeout)
            cluster_id = metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
            
            # Get all consumer groups
            consumer_groups_future = self.client.kafka_client.list_consumer_groups()
            consumer_groups_result = consumer_groups_future.result(timeout=self.config._request_timeout / 1000)
            
            if consumer_groups_result.errors:
                self.log.warning(f"Errors listing consumer groups: {consumer_groups_result.errors}")
            
            consumer_groups = consumer_groups_result.valid
            
            self.log.info(f"Found {len(consumer_groups)} consumer groups")
            
            # Emit metric for number of consumer groups
            self.check.gauge('consumer_group.count', len(consumer_groups), tags=self._get_tags(cluster_id))
            
            # Iterate through each consumer group
            for group in consumer_groups:
                group_id = group.group_id
                group_tags = self._get_tags(cluster_id) + [f'consumer_group:{group_id}']
                
                try:
                    # Get consumer group details
                    futures = self.client.kafka_client.describe_consumer_groups([group_id])
                    
                    for group_id_key, future in futures.items():
                        try:
                            group_info = future.result(timeout=self.config._request_timeout / 1000)
                            
                            # Get group state
                            state = group_info.state
                            members = group_info.members
                            coordinator = group_info.coordinator
                            
                            state_name = state.name if hasattr(state, 'name') else str(state)
                            state_tags = group_tags + [f'state:{state_name}']
                            
                            if coordinator:
                                state_tags.append(f'coordinator:{coordinator.id}')
                            
                            # Emit metrics
                            self.check.gauge('consumer_group.members', len(members), tags=state_tags)
                            
                            # Emit state as a tag instead of value
                            self.check.gauge('consumer_group.state', 1, tags=state_tags)
                            
                            # Process members
                            member_info = []
                            topics_for_group = set()
                            
                            for member in members:
                                member_id = member.member_id
                                client_id = member.client_id
                                host = member.host
                                
                                member_info.append({
                                    'member_id': member_id,
                                    'client_id': client_id,
                                    'host': host
                                })
                                
                                # Extract topics from member assignment
                                if hasattr(member, 'assignment') and member.assignment:
                                    for tp in member.assignment.topic_partitions:
                                        topics_for_group.add(tp.topic)
                            
                        except Exception as e:
                            self.log.warning(f"Error getting consumer group details for {group_id}: {e}")
                        
                except Exception as e:
                    self.log.error(f"Error processing consumer group {group_id}: {e}")
                    
        except Exception as e:
            self.log.error(f"Error collecting consumer group metadata: {e}")
    
    def _collect_schema_registry_info(self):
        """Collect information from Schema Registry."""
        if not self.config._schema_registry_url:
            return
        
        try:
            import requests
            
            self.log.info(f"Collecting schema registry information from {self.config._schema_registry_url}")
            
            # Get cluster_id
            metadata = self.client.kafka_client.list_topics(timeout=self.config._request_timeout)
            cluster_id = metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown'
            
            # Get all subjects (schemas)
            response = requests.get(
                f"{self.config._schema_registry_url}/subjects", 
                timeout=10
            )
            response.raise_for_status()
            
            subjects = response.json()
            
            self.log.info(f"Found {len(subjects)} schemas in schema registry")
            
            # Emit metric for number of schemas
            self.check.gauge('schema_registry.subjects', len(subjects), tags=self._get_tags(cluster_id))
            
            # Get details for each subject
            for subject in subjects:
                subject_tags = self._get_tags(cluster_id) + [f'subject:{subject}']
                
                try:
                    # Get versions for this subject
                    versions_response = requests.get(
                        f"{self.config._schema_registry_url}/subjects/{subject}/versions",
                        timeout=10
                    )
                    versions_response.raise_for_status()
                    versions = versions_response.json()
                    
                    # Emit metric for number of versions
                    self.check.gauge('schema_registry.versions', len(versions), tags=subject_tags)
                    
                    # Get latest version details
                    latest_response = requests.get(
                        f"{self.config._schema_registry_url}/subjects/{subject}/versions/latest",
                        timeout=10
                    )
                    latest_response.raise_for_status()
                    latest_schema = latest_response.json()
                    
                    schema_id = latest_schema.get('id')
                    schema_version = latest_schema.get('version')
                    schema_type = latest_schema.get('schemaType', 'AVRO')
                    schema_content = latest_schema.get('schema', '')
                    
                    # Extract topic name and schema type (key/value) from subject
                    # Subjects typically follow patterns: "topic-key", "topic-value"
                    topic_name = subject
                    schema_for = 'unknown'
                    
                    if subject.endswith('-value'):
                        topic_name = subject[:-6]  # Remove '-value'
                        schema_for = 'value'
                    elif subject.endswith('-key'):
                        topic_name = subject[:-4]  # Remove '-key'
                        schema_for = 'key'
                    
                    # Create event with schema content only in msg_text
                    # All metadata goes into tags for easy querying
                    event_tags = subject_tags + [
                        f'schema_id:{schema_id}', 
                        f'schema_version:{schema_version}', 
                        f'schema_type:{schema_type}',
                        f'topic:{topic_name}',
                        f'schema_for:{schema_for}',
                        'event_type:schema_registry'
                    ]
                    
                    self.check.event({
                        'timestamp': int(time.time()),
                        'event_type': 'info',
                        'source_type_name': 'kafka',
                        'msg_title': f'{topic_name} ({schema_for}) - Schema v{schema_version}',
                        'msg_text': schema_content,
                        'tags': event_tags,
                        'aggregation_key': f'kafka_schema_{subject}_{schema_version}',
                        'alert_type': 'info'
                    })
                    
                except Exception as e:
                    self.log.warning(f"Error getting schema details for {subject}: {e}")
            
        except Exception as e:
            self.log.error(f"Error collecting schema registry information: {e}")
    
    def _get_tags(self, cluster_id: str | None = None) -> list[str]:
        """Get base tags with kafka_cluster_id."""
        tags = list(self.config._custom_tags)
        if cluster_id:
            tags.append(f'kafka_cluster_id:{cluster_id}')
        return tags


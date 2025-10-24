# Kafka Consumer Integration - Comprehensive Cluster Monitoring

## Overview

This document provides a complete summary of the enhanced Kafka Consumer integration that collects extensive metadata about Kafka clusters, including broker configurations, topic information, partition details, consumer groups, and schema registry data.

## What Was Done

### 1. **Extended kafka_consumer Integration**
Instead of creating a new integration, we extended the existing `kafka_consumer` integration to include comprehensive cluster metadata collection. This approach was chosen because:
- The `kafka_consumer` integration already uses `confluent-kafka` library
- It provides a natural fit for monitoring both consumers and cluster health
- Single configuration for users
- Less code duplication

### 2. **New Features Added**

#### A. Broker Metadata Collection
- **Broker Discovery**: Automatically discovers all brokers in the cluster
- **Broker Configuration**: Collects detailed configuration for each broker including:
  - `advertised.listeners`
  - `auto.create.topics.enable`
  - `log.dirs`
  - `log.retention.bytes`
  - `log.retention.ms`
  - `log.segment.bytes`
  - `num.partitions`
  - `default.replication.factor`
  - `min.insync.replicas`
- **Broker Load Distribution**: Tracks leader count and partition distribution per broker

#### B. Topic & Partition Metadata
- **Topic Discovery**: Lists all topics in the cluster
- **Partition Details**: For each partition:
  - Beginning offset (low watermark)
  - End offset (high watermark)
  - Partition size (number of messages)
  - Leader broker
  - Replica count
  - In-Sync Replicas (ISR)
  - Under-replicated status
  - Offline status
- **Message Rate**: Calculates message production rate per topic

#### C. Consumer Group Metadata
- **Consumer Group Discovery**: Lists all consumer groups
- **Group State**: Monitors consumer group state (STABLE, REBALANCING, DEAD, EMPTY)
- **Group Members**: Tracks members in each group with details:
  - Member ID
  - Client ID
  - Host
  - Assigned partitions
- **Consumer Lag**: Provides both message-based and time-based lag

#### D. Schema Registry Integration
- **Schema Discovery**: Lists all registered schemas
- **Schema Versions**: Tracks version count per subject
- **Schema Details**: Collects schema ID, version, and type (AVRO, Protobuf, JSON)

### 3. **New Configuration Options**

All options are added to the `kafka_consumer` check configuration:

```yaml
instances:
  - kafka_connect_str: kafka:29092
    
    # Enable cluster metadata collection features
    collect_broker_metadata: true          # Collect broker info and configs
    collect_topic_metadata: true           # Collect topic and partition details
    collect_consumer_group_metadata: true  # Collect consumer group info
    collect_schema_registry: true          # Collect schema registry data
    
    # Schema Registry URL (required if collect_schema_registry is true)
    schema_registry_url: http://schema-registry:8081
    
    # Enable data streams for lag in seconds
    data_streams_enabled: true
    
    # Monitor all consumer groups
    monitor_unlisted_consumer_groups: true
    
    # Collection interval (seconds)
    min_collection_interval: 30
```

### 4. **Metrics Collected**

All metrics are tagged with `kafka_cluster_id` for proper filtering.

#### Broker Metrics
- `kafka.broker.count` - Total number of brokers
- `kafka.broker.leader_count` - Number of leader partitions per broker
- `kafka.broker.partition_count` - Total partitions per broker (including replicas)
- `kafka.broker.config.*` - Broker configuration values (as gauges)

#### Topic Metrics
- `kafka.topic.count` - Total number of topics
- `kafka.topic.partitions` - Number of partitions per topic
- `kafka.topic.size` - Total messages in topic
- `kafka.topic.message_rate` - Messages produced per second

#### Partition Metrics
- `kafka.partition.beginning_offset` - Low watermark
- `kafka.partition.end_offset` - High watermark
- `kafka.partition.size` - Number of messages in partition
- `kafka.partition.replicas` - Number of replicas
- `kafka.partition.isr` - Number of in-sync replicas
- `kafka.partition.under_replicated` - 1 if under-replicated, 0 otherwise
- `kafka.partition.offline` - 1 if offline (no leader), 0 otherwise

#### Consumer Group Metrics
- `kafka.consumer_group.count` - Total consumer groups
- `kafka.consumer_group.members` - Members per group
- `kafka.consumer_group.state_value` - Numeric state (1=STABLE, 0.5=REBALANCING, 0=DEAD/EMPTY)
- `kafka.consumer_offset` - Current consumer offset
- `kafka.consumer_lag` - Messages behind (lag by message count)
- `kafka.estimated_consumer_lag_seconds` - Lag in seconds (requires data_streams_enabled)
- `kafka.broker_offset` - High watermark for the partition

#### Schema Registry Metrics
- `kafka.schema_registry.subjects` - Total number of schemas
- `kafka.schema_registry.versions` - Version count per subject

### 5. **Events Collected**

Events use proper Datadog event structure with `source_type_name: kafka` and tagged with `event_type` for filtering.

#### Broker Events
- **Type**: `config_change`
- **Tag**: `event_type:broker_config`
- **Content**: Full broker configuration snapshot
- **When**: Periodically or on configuration change

#### Consumer Group Events
- **Type**: `info` or `warning`
- **Tag**: `event_type:consumer_group`
- **Content**: Group state, member count, member details
- **When**: When group is not STABLE or has members (state changes)

#### Schema Registry Events
- **Type**: `info`
- **Tag**: `event_type:schema_registry`
- **Content**: Schema subject, ID, version, type
- **When**: Schema registration or version update

### 6. **Dashboard**

A comprehensive Datadog dashboard (`kafka_cluster_dashboard.json`) with:

#### Template Variables
- `$kafka_cluster_id` - Filter by cluster ID
- `$topic` - Filter by topic name
- `$consumer_group` - Filter by consumer group
- `$broker_id` - Filter by broker ID

#### Dashboard Sections
1. **Overview**: Total brokers, topics, consumer groups, total messages
2. **Broker Metrics**: Broker count, leader distribution, partition distribution, configurations
3. **Topic Metrics**: Topic count, partitions per topic, top topics by size, message rate
4. **Partition Metrics**: Offsets, sizes, replication health, under-replicated/offline alerts
5. **Consumer Group Metrics**: Group count, members, state, offsets, **lag in messages and seconds**
6. **Schema Registry**: Schema count, versions
7. **Advanced Metrics**: Message production rate, broker load distribution, consumer lag in seconds
8. **Events**: All Kafka events filtered by type (broker config, consumer groups, schemas)

#### Total Widgets: **45 widgets**
- 37 metric visualizations
- 5 event streams
- 1 event timeline
- 2 informational notes

### 7. **Docker Compose Setup**

Complete testing environment with:
- **Kafka Broker** (Confluent Platform 7.5.0)
- **Zookeeper**
- **Schema Registry**
- **Continuous Producer** - Produces messages to 6 topics every 10 seconds
- **5 Consumer Groups**:
  - `order-processors` - Fast consumer (orders topic)
  - `user-service` - Medium consumer (users topic)
  - `analytics-service` - **Slow consumer** (events topic) - creates lag
  - `multi-topic-consumer` - Consumes from multiple topics
  - `reporting-service` - Medium consumer (events topic)
- **Schema Initialization** - Registers 5 AVRO schemas on startup
- **Datadog Agent** - Configured with the kafka_consumer integration

#### Starting the Environment

```bash
cd kafka_consumer
docker compose -f docker-compose-test.yml up -d
```

This single command:
1. Starts Kafka infrastructure
2. Creates 6 topics (orders, users, events, payments, analytics, notifications)
3. Registers 5 AVRO schemas
4. Starts continuous producers
5. Starts 5 consumer groups
6. Starts Datadog Agent with the integration

### 8. **Key Changes to Files**

#### Modified Files
- `kafka_consumer/datadog_checks/kafka_consumer/kafka_consumer.py` - Added cluster metadata collector initialization and execution
- `kafka_consumer/datadog_checks/kafka_consumer/config.py` - Added new configuration options
- `kafka_consumer/datadog_checks/kafka_consumer/cluster_metadata.py` - **NEW FILE** - Core logic for metadata collection
- `kafka_consumer/pyproject.toml` - Added `requests` dependency for Schema Registry
- `kafka_consumer/datadog_checks/kafka_consumer/data/conf.yaml.example` - Documented new options
- `kafka_consumer/conf.yaml` - Agent configuration for testing
- `kafka_consumer/docker-compose-test.yml` - Complete testing environment

#### New Files
- `kafka_consumer/datadog_checks/kafka_consumer/cluster_metadata.py` - Metadata collection logic
- `kafka_consumer/kafka_cluster_dashboard.json` - Dashboard JSON
- `KAFKA_CLUSTER_METADATA_COLLECTION.md` - Original documentation
- `KAFKA_INTEGRATION_SUMMARY.md` - This summary

### 9. **Benefits for Kafka Administrators**

#### Operational Visibility
- **Capacity Planning**: Track partition and leader distribution across brokers
- **Performance Monitoring**: Monitor message production rates and consumer lag
- **Health Monitoring**: Identify under-replicated and offline partitions
- **Consumer Health**: Monitor consumer group stability and lag

#### Troubleshooting
- **Lag Analysis**: Both message-based and time-based lag metrics
- **Rebalancing Detection**: Events and metrics for consumer group state changes
- **Configuration Auditing**: Track broker configuration changes
- **Schema Evolution**: Monitor schema versions and updates

#### Alerting Opportunities
- Alert on under-replicated partitions
- Alert on offline partitions
- Alert on excessive consumer lag (messages or seconds)
- Alert on consumer group rebalancing
- Alert on broker configuration changes
- Alert on slow consumers (lag in seconds)

### 10. **Testing & Validation**

#### Verify Integration is Running
```bash
docker exec datadog-agent agent status | grep kafka_consumer
```

Expected output:
```
kafka_consumer (6.9.0)
----------------------
  Instance ID: kafka_consumer:79a386e73ef3d0b7 [OK]
  Total Runs: X
  Metric Samples: Last Run: ~600+
  Events: Last Run: 5+
```

#### Run Check Manually
```bash
docker exec datadog-agent agent check kafka_consumer
```

#### View Metrics in Datadog
1. Go to Metrics Explorer: https://app.datadoghq.com/metric/explorer
2. Search for: `kafka.broker.count`, `kafka.topic.count`, `kafka.consumer_lag`, etc.
3. Filter by `kafka_cluster_id`

#### View Events in Datadog
1. Go to Events Explorer: https://app.datadoghq.com/event/explorer
2. Search for: `source:kafka`
3. Filter by tags: `event_type:broker_config`, `event_type:consumer_group`, `event_type:schema_registry`

#### Import Dashboard
1. Go to: https://app.datadoghq.com/dashboard/lists
2. Click "New Dashboard" → Import dashboard JSON
3. Paste contents of `kafka_cluster_dashboard.json`
4. Or use the API:
```bash
curl -X POST "https://app.datadoghq.com/api/v1/dashboard" \
  -H "DD-API-KEY: YOUR_API_KEY" \
  -H "DD-APPLICATION-KEY: YOUR_APP_KEY" \
  -H "Content-Type: application/json" \
  -d @kafka_consumer/kafka_cluster_dashboard.json
```

## Summary of All Changes

### What Was Requested
✅ Size of each topic - `kafka.topic.size`
✅ Size of each partition - `kafka.partition.size`
✅ Low & High offsets - `kafka.partition.beginning_offset`, `kafka.partition.end_offset`
✅ Broker configuration - All configs as metrics and events
✅ List consumer groups - `kafka.consumer_group.count` + details
✅ List topics per consumer group - In consumer group events
✅ List members in each consumer group - `kafka.consumer_group.members` + event details
✅ Status of each consumer group - `kafka.consumer_group.state_value`
✅ Schemas from schema registry - `kafka.schema_registry.subjects` + events
✅ **Lag by message** - `kafka.consumer_lag`
✅ **Lag in seconds** - `kafka.estimated_consumer_lag_seconds` (via data_streams_enabled)

### Additional Features Added
✅ Message production rate per topic
✅ Leader count per broker
✅ Partition distribution per broker
✅ Under-replicated partition detection
✅ Offline partition detection
✅ Consumer group rebalancing detection
✅ Schema version tracking
✅ Proper event tagging with `kafka_cluster_id`
✅ Comprehensive dashboard with 45 widgets
✅ Complete Docker Compose testing environment
✅ Continuous producers and consumers for realistic testing
✅ Schema registry with 5 registered schemas

## Next Steps

1. **Import the Dashboard** to visualize all metrics
2. **Set up Alerts** for critical conditions:
   - Under-replicated partitions > 0
   - Offline partitions > 0
   - Consumer lag > threshold
   - Consumer group not STABLE
3. **Adjust Collection Interval** based on cluster size (default: 30s)
4. **Monitor Performance** of the integration itself
5. **Customize Dashboard** based on your specific needs

## Testing Configuration

To test this integration:
1. Create a `.env` file in `kafka_consumer/` directory with your Datadog API key:
   ```bash
   DD_API_KEY=your_datadog_api_key_here
   ```
2. See `kafka_consumer/README_TESTING.md` for complete setup instructions
3. Run: `docker compose -f docker-compose-test.yml up -d`

The test environment uses:
- **DD_SITE**: `datadoghq.com`
- **Hostname**: `kafka-test-agent`

## Support

For issues or questions:
1. Check agent logs: `docker logs datadog-agent | grep kafka_consumer`
2. Run check manually: `docker exec datadog-agent agent check kafka_consumer`
3. Verify Kafka connectivity: `docker exec datadog-agent nc -zv kafka 29092`


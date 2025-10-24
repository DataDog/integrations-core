# Kafka Cluster Metadata Collection - Enhancement Summary

## Overview

I've extended the `kafka_consumer` integration to collect comprehensive Kafka cluster metadata, providing deep visibility into your Kafka infrastructure beyond just consumer lag monitoring.

## What Was Done

### 1. Created New Module: `cluster_metadata.py`
**Location**: `kafka_consumer/datadog_checks/kafka_consumer/cluster_metadata.py`

This module provides a `ClusterMetadataCollector` class that collects:

#### **Broker Metadata**
- Number of brokers in the cluster
- Broker configurations including:
  - `advertised.listeners`
  - `auto.create.topics.enable`
  - `log.dirs`
  - `log.retention.bytes`
  - `log.retention.ms`
  - `log.segment.bytes`
  - `num.partitions`
  - `num.network.threads`
  - `num.io.threads`
  - `default.replication.factor`
  - `min.insync.replicas`

#### **Topic & Partition Metadata**
- Total number of topics
- Number of partitions per topic
- Beginning offset (low watermark) per partition
- End offset (high watermark) per partition
- Partition size (total message count)
- Leader broker for each partition
- Number of replicas per partition
- Number of in-sync replicas (ISR)
- Under-replicated partitions detection
- Offline partitions detection

#### **Consumer Group Metadata**
- Total number of consumer groups
- Consumer group state (STABLE, PREPARING_REBALANCE, COMPLETING_REBALANCE, DEAD, EMPTY)
- Number of members in each consumer group
- Member details:
  - `member_id`
  - `client_id`
  - `host`
- Topics consumed by each consumer group
- Coordinator broker information

#### **Schema Registry Information**
- Total number of schemas (subjects)
- Number of versions per schema
- Latest schema details:
  - Schema ID
  - Schema version
  - Schema type (AVRO, Protobuf, JSON)

### 2. Updated Configuration (`config.py`)
Added new configuration options:
- `collect_broker_metadata` - Enable/disable broker metadata collection
- `collect_topic_metadata` - Enable/disable topic/partition metadata collection
- `collect_consumer_group_metadata` - Enable/disable consumer group metadata collection
- `collect_schema_registry` - Enable/disable schema registry collection
- `schema_registry_url` - URL of the Schema Registry

### 3. Integrated into Main Check (`kafka_consumer.py`)
- Added `ClusterMetadataCollector` instantiation in `__init__`
- Integrated metadata collection into the main `check()` method
- Metadata is collected after consumer offset/lag collection

### 4. Updated Dependencies (`pyproject.toml`)
Added `requests>=2.28.0` for Schema Registry REST API calls

### 5. Updated Configuration Example (`conf.yaml.example`)
Added comprehensive documentation for all new configuration options

## Metrics Collected

All metrics are emitted under the `kafka.` namespace:

### Broker Metrics
- `kafka.broker.count` - Number of brokers in the cluster
- `kafka.broker.config.<config_name>` - Numeric broker configurations

### Topic Metrics
- `kafka.topic.count` - Total number of topics
- `kafka.topic.partitions` - Number of partitions per topic
- `kafka.topic.size` - Total messages in topic (across all partitions)

### Partition Metrics
- `kafka.partition.beginning_offset` - Low watermark (earliest available offset)
- `kafka.partition.end_offset` - High watermark (latest offset)
- `kafka.partition.size` - Number of messages in partition
- `kafka.partition.replicas` - Number of replicas
- `kafka.partition.isr` - Number of in-sync replicas
- `kafka.partition.under_replicated` - 1 if under-replicated, 0 otherwise
- `kafka.partition.offline` - 1 if offline (no leader), 0 otherwise

### Consumer Group Metrics
- `kafka.consumer_group.count` - Total number of consumer groups
- `kafka.consumer_group.members` - Number of members in consumer group
- `kafka.consumer_group.state_value` - Numeric representation of group state (1=STABLE, 0.5=REBALANCING, 0=DEAD/EMPTY)

### Schema Registry Metrics
- `kafka.schema_registry.subjects` - Total number of schemas
- `kafka.schema_registry.versions` - Number of versions per schema

## Events Collected

### Broker Events
- **kafka_broker_info** - Broker discovery events with host/port information
- **kafka_broker_config** - Broker configuration snapshots

### Topic Events
- **kafka_topic_info** - Topic metadata with partition count and message totals

### Consumer Group Events
- **kafka_consumer_group_info** - Comprehensive consumer group information including:
  - State
  - Members
  - Topics
  - Member details (JSON)

### Schema Events
- **kafka_schema_info** - Schema metadata with ID, version, and type

## Configuration Example

```yaml
init_config:

instances:
  - kafka_connect_str: localhost:9092
    
    # Standard kafka_consumer options
    monitor_unlisted_consumer_groups: true
    
    # NEW: Enable cluster metadata collection
    collect_broker_metadata: true
    collect_topic_metadata: true
    collect_consumer_group_metadata: true
    collect_schema_registry: true
    
    # NEW: Schema Registry URL
    schema_registry_url: http://localhost:8081
    
    tags:
      - env:production
      - kafka_cluster:main-cluster
    
    # Recommended: Longer interval for metadata (topology changes less frequently)
    min_collection_interval: 60
```

## How It Works

1. **Uses Existing Infrastructure**: Leverages the existing `KafkaClient` and `confluent-kafka` library already used by `kafka_consumer`

2. **Efficient Collection**: 
   - Reuses existing AdminClient connections
   - Batches requests where possible
   - Only collects what's configured

3. **Tagged Metrics**: All metrics are properly tagged with:
   - `broker_id`, `broker_host`, `broker_port` (broker metrics)
   - `topic`, `partition`, `leader` (topic/partition metrics)
   - `consumer_group`, `state` (consumer group metrics)
   - `subject`, `schema_id`, `schema_version` (schema metrics)
   - Plus any custom tags from configuration

4. **Events for Rich Context**: Complex metadata (broker configs, consumer group members) is sent as events for:
   - Easy querying in Datadog
   - Historical tracking
   - Alerting on topology changes

## Use Cases

### 1. Capacity Planning
- Track topic growth over time (`kafka.topic.size`)
- Monitor partition distribution
- Analyze broker configuration settings

### 2. Health Monitoring
- Detect under-replicated partitions
- Identify offline partitions
- Monitor consumer group rebalancing frequency
- Track consumer group membership changes

### 3. Troubleshooting
- Understand consumer group topology
- Identify which topics are consumed by which groups
- Track schema evolution
- Correlate broker configs with performance issues

### 4. Compliance & Auditing
- Track retention policies across brokers
- Monitor auto-topic creation settings
- Audit schema versions and types

### 5. Product Development
The rich metadata enables building products on top of:
- Kafka topology visualization
- Automated capacity recommendations
- Consumer group health scoring
- Schema governance tools

## Testing

### Docker Environment
A complete test environment is available at:
- Docker Compose: `kafka/docker-compose-simple.yml`
- Includes: Kafka, Zookeeper, Schema Registry
- Pre-populated with test topics, messages, and consumer groups

### Test Configuration
- Configuration file: `kafka_consumer/test_conf.yaml`
- Enables all metadata collection features
- Points to localhost Kafka

### Running Tests
```bash
# Start Kafka environment
cd kafka
docker-compose -f docker-compose-simple.yml up -d

# Wait for setup to complete
sleep 30

# Run the integration (would need Datadog Agent or test script)
# The check will collect all metadata and submit to Datadog
```

## Performance Considerations

1. **Collection Interval**: Metadata doesn't change as frequently as consumer lag
   - Recommended: 60-300 seconds for metadata
   - Keep 15 seconds for standard consumer offset collection

2. **Impact**: Minimal additional load
   - Uses existing connections
   - Batched API calls
   - Optional features (enable only what you need)

3. **Metrics Volume**: 
   - Broker metadata: ~10-50 metrics per broker
   - Topic metadata: ~5-10 metrics per partition
   - Consumer group metadata: ~2-5 metrics per group
   - Schema registry: ~2 metrics per schema

## Future Enhancements

Potential additions:
1. **Quota Information**: Collect producer/consumer quotas
2. **ACL Information**: Security/authorization metadata
3. **Transaction Coordinator Data**: Transaction state information
4. **Controller Information**: Active controller tracking
5. **Log Directory Details**: Per-broker disk usage by topic

## Testing Setup

To test this integration:

1. Create a `.env` file in `kafka_consumer/` directory:
   ```bash
   DD_API_KEY=your_datadog_api_key_here
   ```

2. Start the test environment:
   ```bash
   cd kafka_consumer
   docker compose -f docker-compose-test.yml up -d
   ```

3. See `kafka_consumer/README_TESTING.md` for complete setup instructions and troubleshooting.

## Files Modified/Created

### New Files
- `kafka_consumer/datadog_checks/kafka_consumer/cluster_metadata.py`
- `kafka_consumer/test_conf.yaml`
- `kafka/docker-compose-simple.yml`
- This documentation file

### Modified Files
- `kafka_consumer/datadog_checks/kafka_consumer/kafka_consumer.py`
- `kafka_consumer/datadog_checks/kafka_consumer/config.py`
- `kafka_consumer/datadog_checks/kafka_consumer/data/conf.yaml.example`
- `kafka_consumer/pyproject.toml`

## Benefits Over Separate Integration

By extending `kafka_consumer` instead of creating a new integration:

1. **Single Configuration**: Users configure one integration, not multiple
2. **Shared Infrastructure**: Reuses connections, authentication, SSL/TLS setup
3. **Consistent Tagging**: All Kafka metrics share the same tag structure
4. **Lower Overhead**: One check process instead of multiple
5. **Easier Maintenance**: Single codebase to maintain
6. **Better UX**: Natural extension of existing consumer monitoring

## Conclusion

This enhancement transforms `kafka_consumer` from a consumer-lag-monitoring tool into a comprehensive Kafka observability solution, providing the deep insights needed to build sophisticated monitoring, alerting, and analytics products on top of Kafka infrastructure.


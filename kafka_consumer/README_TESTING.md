e Kafka Consumer Integration - Testing Guide

## Quick Start

### 1. Set up your Datadog API Key

Create a `.env` file in this directory:

```bash
# Copy the template
cp env.template .env

# Edit .env and add your Datadog API key
# DD_API_KEY=your_actual_datadog_api_key_here
```

**Note:** The `.env` file should NOT be committed to git. Make sure it's in `.gitignore`.

### 2. Start the test environment

```bash
docker compose -f docker-compose-test.yml up -d
```

This will start:
- **Kafka Broker** (with Zookeeper)
- **Schema Registry** with 5 registered schemas
- **Continuous Producer** (produces messages every 10 seconds)
- **5 Consumer Groups**:
  - `order-processors` (orders topic)
  - `user-service` (users topic)
  - `analytics-service` (events topic - slow consumer, creates lag)
  - `multi-topic-consumer` (orders, payments, notifications)
  - `reporting-service` (events topic)
- **Datadog Agent** with the kafka_consumer integration

### 3. Verify the integration is running

```bash
docker exec datadog-agent agent status | grep kafka_consumer
```

Expected output:
```
kafka_consumer (6.9.0)
----------------------
  Instance ID: kafka_consumer:79a386e73ef3d0b7 [OK]
  Total Runs: X
  Metric Samples: Last Run: 650+
  Events: Last Run: 14+
```

### 4. View metrics in Datadog

Go to: https://app.datadoghq.com/metric/explorer

Search for:
- `kafka.broker.count`
- `kafka.topic.count`
- `kafka.consumer_lag`
- `kafka.partition.under_replicated`

Filter by: `kafka_cluster_id:WxsTRn91ShWgIdlNQWBTxg`

### 5. View events in Datadog

Go to: https://app.datadoghq.com/event/explorer

Search for: `source:kafka kafka_cluster_id:WxsTRn91ShWgIdlNQWBTxg`

Event types:
- `event_type:broker_config` - Broker configuration (JSON)
- `event_type:topic_config` - Topic-specific overrides (JSON)
- `event_type:schema_registry` - Schema definitions

### 6. Import the dashboard

1. Go to: https://app.datadoghq.com/dashboard/lists
2. Click "New Dashboard" → "Import dashboard JSON"
3. Paste the contents of `kafka_cluster_dashboard.json`
4. Click "Import"

## Test Environment Details

### Topics Created
- `orders` (3 partitions)
- `users` (5 partitions)
- `events` (2 partitions)
- `payments` (1 partition)
- `analytics` (10 partitions)
- `notifications` (4 partitions)

### Schemas Registered
- `users-value` (AVRO)
- `orders-value` (AVRO)
- `payments-value` (AVRO)
- `events-value` (AVRO)
- `notifications-value` (AVRO)

### Consumer Groups
All consumer groups are actively consuming with different speeds to create realistic lag scenarios.

## Stopping the Environment

```bash
docker compose -f docker-compose-test.yml down
```

To also remove volumes:
```bash
docker compose -f docker-compose-test.yml down -v
```

## Configuration

The integration is configured in `conf.yaml`:
- `collect_broker_metadata: true` - Collect broker configs
- `collect_topic_metadata: true` - Collect topic/partition details
- `collect_consumer_group_metadata: true` - Collect consumer group info
- `collect_schema_registry: true` - Collect schemas
- `data_streams_enabled: true` - Enable lag in seconds
- `min_collection_interval: 30` - Collect every 30 seconds

## Troubleshooting

### Check agent logs
```bash
docker logs datadog-agent | grep kafka_consumer
```

### Run the check manually
```bash
docker exec datadog-agent agent check kafka_consumer
```

### Check Kafka connectivity
```bash
docker exec datadog-agent nc -zv kafka 29092
```

### View all events being sent
```bash
docker exec datadog-agent agent check kafka_consumer 2>&1 | grep -A 20 "=== Events ==="
```


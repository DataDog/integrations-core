# Kafka Consumer Integration - Local Testing

## Setup

```bash
# 1. Set your Datadog API key
cp env.template .env
# Edit .env and add DD_API_KEY

# 2. Start everything
docker compose -f docker-compose-test.yml up -d

# 3. Verify
docker exec datadog-agent agent status | grep kafka_consumer
```

## What's Running

- Kafka with 6 topics (orders, users, events, payments, analytics, notifications)
- Schema Registry with 5 AVRO schemas
- Producer generating messages every 10s
- 5 consumer groups (one intentionally slow to create lag)
- Datadog Agent with `enable_cluster_monitoring: true`

## View Data

Metrics: https://app.datadoghq.com/metric/explorer
- Filter by `kafka_cluster_id:WxsTRn91ShWgIdlNQWBTxg`
- Example metrics: `kafka.broker.count`, `kafka.topic.size`, `kafka.consumer_lag`

Dashboard: Import `kafka_cluster_dashboard.json` at https://app.datadoghq.com/dashboard/lists

## Stop

```bash
docker compose -f docker-compose-test.yml down -v
```
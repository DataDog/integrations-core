# Kafka Actions - Local Development & Testing

This directory contains test configurations for the `kafka_actions` integration.

## Prerequisites

1. **Docker Compose Environment**
   ```bash
   cd ../../kafka_consumer/local_dev
   docker compose -f docker-compose-test.yml up -d
   ```

2. **Wait for Services to Start**
   - Zookeeper: `localhost:2181`
   - Kafka: `localhost:9092`
   - Schema Registry: `http://localhost:8081`

3. **Verify Setup**
   ```bash
   # Check topics
   curl -s http://localhost:8081/subjects | jq .
   
   # Should show: orders, users, events, payments, products, notifications
   
   # Check Kafka is producing
   docker logs kafka-producer
   ```

## Test Configurations

### 1. Retrieve Messages (`test_retrieve_messages.yaml`)

Retrieves and filters messages from the `orders` topic, emits as Datadog events.

**Run:**
```bash
# Using ddev
cd ../..
ddev env check kafka_actions --agent-build base:py3.13-3.3 \
  --config-file kafka_actions/local_dev/test_retrieve_messages.yaml

# Or manually (requires DD_API_KEY)
DD_API_KEY=xxx agent check kafka_actions \
  -c kafka_actions/local_dev/test_retrieve_messages.yaml
```

**What it does:**
- Scans up to 100 messages from `orders` topic
- Filters for messages where `amount > 500`
- Emits up to 10 matching messages as Datadog events

**Expected output:**
```
Executing Kafka action: retrieve_messages
Scanned 100 messages, sent 10 as events
```

---

### 2. Produce Message (`test_produce_message.yaml`)

Produces a test message to the `orders` topic.

**Run:**
```bash
ddev env check kafka_actions --agent-build base:py3.13-3.3 \
  --config-file kafka_actions/local_dev/test_produce_message.yaml
```

**What it does:**
- Produces a single test order message
- Key: `test-99999`
- Value: JSON with order details
- Headers: `source`, `test`

**Expected output:**
```
Executing Kafka action: produce_message
Message delivered to orders [0] at offset 123
```

**Verify:**
```bash
# Check the message was produced
docker exec kafka-broker kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic orders --from-beginning --max-messages 1
```

---

### 3. Evolve Schema (`test_evolve_schema.yaml`)

Updates the `products-value` schema with an additional field.

**Run:**
```bash
ddev env check kafka_actions --agent-build base:py3.13-3.3 \
  --config-file kafka_actions/local_dev/test_evolve_schema.yaml
```

**What it does:**
- Adds `updated_at` field to Product schema
- Performs compatibility check
- Registers new schema version

**Expected output:**
```
Executing Kafka action: evolve_schema
Schema compatibility check passed for subject 'products-value'
Schema registered for subject 'products-value' with ID 7
```

**Verify:**
```bash
# Check schema versions
curl -s http://localhost:8081/subjects/products-value/versions | jq .

# Get latest schema
curl -s http://localhost:8081/subjects/products-value/versions/latest | jq .
```

---

### 4. Manage Topic (`test_manage_topic.yaml`)

Creates a new topic with specific configuration.

**Run:**
```bash
ddev env check kafka_actions --agent-build base:py3.13-3.3 \
  --config-file kafka_actions/local_dev/test_manage_topic.yaml
```

**What it does:**
- Creates `test-actions-topic` with 3 partitions
- Sets retention to 1 hour
- Configures snappy compression

**Expected output:**
```
Executing Kafka action: manage_topic
Topic 'test-actions-topic' created successfully
```

**Verify:**
```bash
# List topics
docker exec kafka-broker kafka-topics \
  --list --bootstrap-server localhost:9092

# Describe topic
docker exec kafka-broker kafka-topics \
  --describe --topic test-actions-topic \
  --bootstrap-server localhost:9092
```

---

## Advanced Testing Scenarios

### Replay Messages (DLQ Scenario)

Create a DLQ topic and replay messages:

```yaml
# 1. Create DLQ topic
action: manage_topic
manage_topic:
  operation: create
  topic: orders-dlq
  num_partitions: 3
  replication_factor: 1

# 2. Produce "failed" messages to DLQ
action: produce_message
produce_message:
  topic: orders-dlq
  value: '{"order_id": "failed-123", "status": "failed", "retry_count": 1}'

# 3. Replay from DLQ to main topic
action: replay_messages
replay_messages:
  source_topic: orders-dlq
  dest_topic: orders
  max_messages: 1000
  filters:
    - field: value.retry_count
      operator: lt
      value: "3"
```

### Message Filtering Examples

**Filter by timestamp:**
```yaml
filters:
  - field: timestamp
    operator: gte
    value: "1699999999000"  # Unix timestamp in ms
```

**Filter by nested field:**
```yaml
filters:
  - field: value.user.email
    operator: contains
    value: "@example.com"
```

**Filter by regex:**
```yaml
filters:
  - field: value.order_id
    operator: regex
    value: "^ORD-.*"
```

**Multiple filters (AND logic):**
```yaml
filters:
  - field: value.status
    operator: eq
    value: "failed"
  - field: value.amount
    operator: gt
    value: "1000"
  - field: value.region
    operator: contains
    value: "US"
```

## Troubleshooting

### Connection Issues

```bash
# Check Kafka is running
docker ps | grep kafka

# Check connectivity
telnet localhost 9092

# Check broker logs
docker logs kafka-broker
```

### No Messages Retrieved

```bash
# Verify messages exist
docker exec kafka-broker kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic orders --from-beginning --max-messages 10

# Check producer is running
docker logs kafka-producer
```

### Schema Registry Issues

```bash
# Check Schema Registry is up
curl http://localhost:8081/

# List all subjects
curl http://localhost:8081/subjects

# Check specific schema
curl http://localhost:8081/subjects/products-value/versions/latest
```

## Cleanup

```bash
# Stop Docker environment
cd ../../kafka_consumer/local_dev
docker compose -f docker-compose-test.yml down

# Remove volumes (complete cleanup)
docker compose -f docker-compose-test.yml down -v
```

## Integration with CI/CD

The kafka_actions check can be integrated into operational workflows:

1. **Scheduled DLQ Replay**: Run replay action on schedule
2. **Schema Deployment**: Automate schema evolution
3. **Topic Provisioning**: Create topics via CI/CD
4. **Message Inspection**: Debug production issues

## Metrics to Monitor

All actions emit metrics:

```
kafka_actions.action.{action_name}.success
kafka_actions.action.{action_name}.failure
kafka_actions.messages.scanned
kafka_actions.messages.sent
kafka_actions.message.produced
kafka_actions.messages.replayed
kafka_actions.topic.created
kafka_actions.schema.registered
```

View in Datadog:
```
avg:kafka_actions.messages.sent{env:test}
count:kafka_actions.action.retrieve_messages.success{*}
```


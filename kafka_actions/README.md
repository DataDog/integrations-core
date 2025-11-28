# Kafka Actions

<div class="alert alert-danger">
This integration is in Preview. To access and use this feature, reach out to the Data Streams Monitoring team at Datadog.
</div>

## Overview

The Kafka Actions integration enables one-time administrative and operational actions on Kafka clusters through the Datadog Agent.

<div class="alert alert-warning">
This integration is exclusively triggered through Remote Configuration and should never be scheduled manually in your Agent configuration. It is not meant to run continuously like traditional checks.
</div>

### Supported Actions

| Action | Description |
|--------|-------------|
| `read_messages` | Read and filter messages with jq-style expressions, supporting JSON, string, BSON, Avro, and Protobuf formats |
| `produce_message` | Produce messages to topics with base64-encoded payloads and headers |
| `create_topic` | Create topics with custom partitions, replication factor, and configurations |
| `update_topic_config` | Update topic configurations and partition counts |
| `delete_topic` | Delete topics |
| `delete_consumer_group` | Delete consumer groups |
| `update_consumer_group_offsets` | Reset consumer group offsets to specific positions |

## Setup

### Installation

The Kafka Actions integration is included in the [Datadog Agent][1] package (version 7.0+).

### Configuration

<div class="alert alert-warning">
<strong>Do not configure this check manually</strong>. This integration is triggered exclusively through Remote Configuration from the Datadog UI.
</div>

Actions are configured and triggered from the Datadog platform, with results visible in the [Events Explorer][3].

## Data Collected

### Events

- **Action Events** (`kafka_action_success` / `kafka_action_error`): Emitted when an action completes
- **Message Events** (`kafka_message`): Emitted for each message retrieved by `read_messages`

### Metrics

This integration does not collect metrics.

### Service Checks

This integration does not include service checks.

## Troubleshooting

### Actions not executing
1. Confirm the Agent version meets minimum requirements
2. Verify Remote Configuration is enabled on your Agent.
3. Check Agent logs for errors.

### Message deserialization failures
Ensure the correct format is specified (`json`, `string`, `bson`, `avro`, `protobuf`) and provide schemas for Avro/Protobuf.

Need help? Contact [Datadog support][2] or reach out to the **Data Streams Monitoring team** at Datadog for questions about this integration.

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/help/
[3]: https://app.datadoghq.com/event/explorer

# Agent Check: Zookeeper

## Overview

The Zookeeper check tracks client connections and latencies, monitors the number of unprocessed requests, and more.

## Setup
### Installation

The Zookeeper check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Zookeeper servers. If you need the newest version of the check, install the `dd-check-zk` package.

### Configuration

Create a file `zk.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - host: localhost
    port: 2181
    timeout: 3
```

Restart the Agent to start sending Zookeeper metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `zk` under the Checks section:

```
  Checks
  ======
    [...]

    zk
    -------
      - instance #0 [OK]
      - Collected 14 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The Zookeeper check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/zookeeper/metadata.csv) for a list of metrics provided by this check.

### Events
The Zookeeper check does not include any event at this time.

### Service Checks

**zookeeper.ruok**:

Returns CRITICAL if Zookeeper does not respond to the Agent's 'ruok' request, otherwise OK.

**zookeeper.mode**:

The Agent submits this service check if `expected_mode` is configured in `zk.yaml`. The check returns OK when Zookeeper's actual mode matches `expected_mode`, otherwise CRITICAL.

## Troubleshooting

If you have any questions about Datadog or a use case our [Docs](https://docs.datadoghq.com/) didn’t mention, we’d love to help! Here’s how you can reach out to us:

### Visit the Knowledge Base

Learn more about what you can do in Datadog on the [Support Knowledge Base](https://datadog.zendesk.com/agent/).

### Web Support

Messages in the [event stream](https://app.datadoghq.com/event/stream) containing **@support-datadog** will reach our Support Team. This is a convenient channel for referencing graph snapshots or a particular event. In addition, we have a livechat service available during the day (EST) from any page within the app.

### By Email

You can also contact our Support Team via email at [support@datadoghq.com](mailto:support@datadoghq.com).

### Over Slack

Reach out to our team and other Datadog users on [Slack](http://chat.datadoghq.com/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
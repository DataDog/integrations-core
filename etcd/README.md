# Etcd Integration

## Overview

Collect etcd metrics to:

* Monitor the health of your etcd cluster.
* Know when host configurations may be out of sync.
* Correlate the performance of etcd with the rest of your applications.

## Setup
### Installation

The etcd check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your etcd instance(s).

### Configuration

Create a file `etcd.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - url: "https://server:port" # API endpoint of your etcd instance
```

Restart the Agent to begin sending etcd metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `etcd` under the Checks section:

```
  Checks
  ======
    [...]

    etcd
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 0 service checks

    [...]
```

## Compatibility

The etcd check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/etcd/metadata.csv) for a list of metrics provided by this integration.

### Events
The Etcd check does not include any event at this time.

### Service Checks

`etcd.can_connect`:

Returns 'Critical' if the Agent cannot collect metrics from your etcd API endpoint.

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
To get a better idea of how (or why) to integrate etcd with Datadog, check out our [blog post](https://www.datadoghq.com/blog/monitor-etcd-performance/) about it.

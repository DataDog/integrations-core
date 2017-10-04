# Ceph Integration

## Overview

Enable the Datadog-Ceph integration to:

  * Track disk usage across storage pools
  * Receive service checks in case of issues
  * Monitor I/O performance metrics

## Setup
### Installation

The Ceph check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Ceph servers.

### Configuration

Create a file `ceph.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - ceph_cmd: /path/to/your/ceph # default is /usr/bin/ceph
    use_sudo: true               # only if the ceph binary needs sudo on your nodes
```

If you enabled `use_sudo`, add a line like the following to your `sudoers` file:

```
dd-agent ALL=(ALL) NOPASSWD:/path/to/your/ceph
```

### Validation

Run the Agent's `info` subcommand and look for `ceph` under the Checks section:

```
  Checks
  ======
    [...]

    ceph
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/ceph/metadata.csv) for a list of metrics provided by this integration.

### Events
The Ceph check does not include any event at this time.

### Service Checks
The Ceph check does not include any service check at this time.

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
To get a better idea of how (or why) to integrate your Ceph cluster with Datadog, check out our [blog post](https://www.datadoghq.com/blog/monitor-ceph-datadog/) about it.

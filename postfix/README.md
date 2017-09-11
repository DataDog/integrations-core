# Postfix Check

## Overview

This check monitors the size of all your Postfix queues.

## Setup
### Installation

The Postfix check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Postfix servers. If you need the newest version of the check, install the `dd-check-postfix` package.

### Configuration

Create a file `postfix.yaml` in the Agent's `conf.d` directory:

```
init_config:
  - postfix_user: postfix

instances:
  # add one instance for each postfix service you want to track
  - directory: /var/spool/postfix
    queues:
      - incoming
      - active
      - deferred
#   tags:
#     - optional_tag1
#     - optional_tag2
```

For each mail queue in `queues`, the Agent forks a `find` on its directory.
It uses `sudo` to do this with the privileges of the postfix user, so you must
add the following lines to `/etc/sudoers` for the Agent's user, `dd-agent`,
assuming postfix runs as `postfix`:
```
dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/incoming -type f
dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/active -type f
dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/deferred -type f
```

Restart the Agent to start sending Postfix metrics to Datadog.

### Validation

Run the Agent's `info` subcommand and look for `postfix` under the Checks section:

```
  Checks
  ======
    [...]

    postfix
    -------
      - instance #0 [OK]
      - Collected 3 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The postfix check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/postfix/metadata.csv) for a list of metrics provided by this check.

### Events
The Postfix check does not include any event at this time.

### Service Checks
The Postfix check does not include any service check at this time.

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
### Blog Article 
To get a better idea of how (or why) to monitor Postfix queue performance with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-postfix-queues/) about it.

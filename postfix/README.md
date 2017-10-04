# Postfix Check

## Overview

This check monitors the size of all your Postfix queues.

## Setup
### Installation

The Postfix check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Postfix servers. If you need the newest version of the check, install the `dd-check-postfix` package.

## Configuration
This check can be configured to use the `find` command which requires granting the dd-agent user sudo access to get a count of messages in the `incoming`, `active`, and `deferred` mail queues.

Optionally, you can configure the agent to use a built in `postqueue -p` command to get a count of messages in the `active`, `hold`, and `deferred` mail queues. `postqueue` is exectued with set-group ID privileges without the need for sudo.

**WARNING**: Using `postqueue` to monitor the mail queues will not report a count of messages for the `incoming` queue.

### Using sudo
Create a file `postfix.yaml` in the Agent's `conf.d` directory:

```
init_config:
  postfix_user: postfix

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
It uses `sudo` to do this with the privileges of the Postfix user, so you must
add the following lines to `/etc/sudoers` for the Agent's user, `dd-agent`,
assuming Postfix runs as `postfix`:
```
dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/incoming -type f
dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/active -type f
dd-agent ALL=(postfix) NOPASSWD:/usr/bin/find /var/spool/postfix/deferred -type f
```
### Using postqueue
Create a file `postfix.yaml` in the Agent's `conf.d` directory:

```
init_config:
  postqueue: true

instances:
  # The config_directory option only applies when `postqueue: true`.
  # The config_directory is the location of the Postfix configuration directory
  # where main.cf lives.
  - config_directory: /etc/postfix
#   tags:
#     - optional_tag
#     - optional_tag0
```
For each `config_directory` in `instances`, the Agent forks a `postqueue -c` for
the Postfix configuration directory.

Postfix has internal access controls that limit activities on the mail queue. By default,
Postfix allows `anyone` to view the queue. On production systems where the Postfix installation
may be configured with stricter access controls, you may need to grant the dd-agent user access to view
the mail queue.

    postconf -e "authorized_mailq_users = dd-agent"        

http://www.postfix.org/postqueue.1.html

            authorized_mailq_users (static:anyone)
                List of users who are authorized to view the queue.


[Restart the Agent](https://help.datadoghq.com/hc/en-us/articles/203764515-Start-Stop-Restart-the-Datadog-Agent) to start sending Postfix metrics to Datadog.

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
To get a better idea of how (or why) to monitor Postfix queue performance with Datadog, check out our [series of blog posts](https://www.datadoghq.com/blog/monitor-postfix-queues/) about it.

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
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitor Postfix queue performance](https://www.datadoghq.com/blog/monitor-postfix-queues/)

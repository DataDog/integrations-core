# Postfix Check

# Overview

This check monitors the size of all your Postfix queues.

# Installation

The Postfix check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Postfix servers. If you need the newest version of the check, install the `dd-check-postfix` package.

# Configuration

Create a file `postfix.yaml` in the Agent's `conf.d` directory:

```
init_config:

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

For each mail queue in `queues`, the Agent forks a `find` on its directory. It uses `sudo`to do this, so you must add the following lines to `/etc/sudoers` for the Agent's user, `dd-agent`:

```
dd-agent ALL=(ALL) NOPASSWD:/usr/bin/find /var/spool/postfix/incoming -type f
dd-agent ALL=(ALL) NOPASSWD:/usr/bin/find /var/spool/postfix/active -type f
dd-agent ALL=(ALL) NOPASSWD:/usr/bin/find /var/spool/postfix/deferred -type f
```

Restart the Agent to start sending Postfix metrics to Datadog.

# Validation

Run the Agent's `info` subcommand and look for postfix` under the Checks section:

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

# Compatibility

The postfix check is compatible with all major platforms.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/postfix/metadata.csv) for a list of metrics provided by this check.
# Postfix Integration

## Overview

Get metrics from postfix service in real time to:

* Visualize and monitor postfix states
* Be notified about postfix failovers and events.

## Installation

Install the `dd-check-postfix` package manually or with your favorite configuration manager

## Configuration

* Edit the `postfix.yaml` file to point to your postfix spool/queues directory (e.g. `/var/spool/postfix)..
* Add a few mail queues to monitor (e.g. `incoming`, `active`, and `deferred`).
* Update `/etc/sudoers` to allow `dd-agent` to run `find /path/to/postfix/spool/* -type f`.

Example:

```yaml
init_config:

instances:
  - directory: /var/spool/postfix
    queues:
      - incoming
      - active
      - deferred
```

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        postfix
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The postfix check is compatible with all major platforms

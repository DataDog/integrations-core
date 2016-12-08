# Gearmand Integration

## Overview

Bring Gearman metrics to Datadog to:

* Visualize Gearman performance.
* Know how many tasks are queued or running.
* Correlate the performance of Gearman with the rest of your applications.

## Installation

Install the `dd-check-gearmand` package manually or with your favorite configuration manager

## Configuration

Configure the Agent to connect to Gearman
Edit conf.d/gearmand.yaml

```
init_config:

instances:
  - server: localhost
    port: 4730
    tags:
        - optional_tag_1
        - optional_tag_2
```

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        gearmand
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The gearmand check is compatible with all major platforms

# Varnish Integration

## Overview

Connect Varnish to Datadog in order to:

* Visualize your cache performance in real-time
* Correlate the performance of Varnish with the rest of your applications

## Installation

Install the `dd-check-varnish` package manually or with your favorite configuration manager

## Configuration

Configure the Agent to connect to Varnish

Edit conf.d/varnish.yaml
```
init_config:

instances:
    - varnishstat: /usr/bin/varnishstat
      tags:
          - instance:production
```

Note: If you're running Varnish 4.1+, you must also add the dd-agent user to the varnish group.
```
sudo usermod -a -G varnish dd-agent
```

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        varnish
        -------
          - instance #0 [OK]
          - Collected 8 metrics & 0 events

## Compatibility

The Varnish check is compatible with all major platforms

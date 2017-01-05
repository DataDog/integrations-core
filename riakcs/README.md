# Riakcs Integration

## Overview

Capture RiakCS metrics in Datadog to:

* Visualize key RiakCS metrics.
* Correlate RiakCS performance with the rest of your applications.

## Installation

Install the `dd-check-riakcs` package manually or with your favorite configuration manager

## Configuration

1. Edit conf.yaml:

```
init_config:

instances:
  - access_id: access-key
    access_secret: access-secret
    #is_secure: True  # Uncomment and change to false if you are not using ssl
    #host: localhost  # Hostname/IP of your riakcs node
    #port: 8080  # port used by your riakcs node
    #s3_root: s3.amazonaws.com # 
```

2. Restart the Agent

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        riakcs
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The riakcs check is compatible with all major platforms

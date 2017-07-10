# Nagios Check

# Overview

Get metrics from nagios service in real time to:

* Visualize and monitor nagios states
* Be notified about nagios failovers and events.

# Installation

Install the `dd-check-nagios` package manually or with your favorite configuration manager

# Configuration

Edit the `nagios.yaml` file to point to your server and port, set the masters to monitor

# Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        nagios
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

# Compatibility

The nagios check is compatible with all major platforms

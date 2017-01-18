# Activemq_xml Integration

## Overview

Get metrics from activemq_xml service in real time to:

* Visualize and monitor activemq_xml states
* Be notified about activemq_xml failovers and events.

## Installation

Install the `dd-check-activemq_xml` package manually or with your favorite configuration manager

## Configuration

Edit the `activemq_xml.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        activemq_xml
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The activemq_xml check is compatible with all major platforms

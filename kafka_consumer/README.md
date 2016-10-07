# Kafka_consumer Integration

## Overview

Get metrics from kafka_consumer service in real time to:

* Visualize and monitor kafka_consumer states
* Be notified about kafka_consumer failovers and events.

## Installation

Install the `dd-check-kafka_consumer` package manually or with your favorite configuration manager

## Configuration

Edit the `kafka_consumer.yaml` file to point to your server and port, set the masters to monitor

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        kafka_consumer
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The kafka_consumer check is compatible with all major platforms

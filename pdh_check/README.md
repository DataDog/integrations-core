# Wmi_check Integration

## Overview

Get metrics from Windows performance counters in real time to:

* Visualize and monitor windows performance counters

## Setup
### Installation

Install the `dd-check-pdh_check` package manually or with your favorite configuration manager

### Configuration

Edit the `pdh_check.yaml` file to collect Windows performance data. See the [sample pdh_check.yaml](https://github.com/DataDog/integrations-core/blob/master/pdh_check/conf.yaml.example) for all available configuration options.

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `pdh_check` under the Checks section:

    Checks
    ======

        pdh_check
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The pdh_check check is compatible with Windows.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/pdh_check/metadata.csv) for a list of metrics provided by this integration.

### Events
The PDH check does not include any event at this time.

### Service Checks
The PDH check does not include any service check at this time.
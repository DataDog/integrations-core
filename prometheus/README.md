# Prometheus Integration

## Overview

Extract custom metrics from any prometheus endpoints.

⚠️ All the metrics retrieved by this integration will be considered as custom metrics

## Configuration

Edit the `prometheus.yaml` file to add your different prometheus instances you want to retrieve metrics from.

Each instance is at least composed of:

* a `prometheus_url` that points to the metric route
* a `namespace` that will be prepended to all metrics (to avoid name collision, ⚠️ this has to be unique)
* a list of `metrics` that you want to retrieve as custom metrics, for each metric you can either
simply add it to the list `- metric_name` or renaming it like `- metric_name: renamed`

There is also a couple of more advanced settings (ssl, labels joining, custom tags,...) that are documented in the [example configuration](conf.yaml.example)

If you are monitoring an off-the-shelf software and you think it would deserve an official integration, have a look at `kube-proxy` for an example, and don't hesitate to contribute.

## Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `prometheus` under the Checks section:

    Checks
    ======

        prometheus
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The prometheus check is compatible with all major platforms

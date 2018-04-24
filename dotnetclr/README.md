# Dotnetclr Integration

## Overview

Get metrics from dotnetclr service in real time to:

* Visualize and monitor dotnetclr states
* Be notified about dotnetclr failovers and events.

## Installation

The Dotnetclr check is packaged with the Agent, so simply [install the Agent][1] on your servers.

## Configuration

Edit the `dotnetclr.yaml` file to point to your server and port, set the masters to monitor

## Validation

[Run the Agent's `status` subcommand][2] and look for `dotnetclr` under the Checks section:

    Checks
    ======

        dotnetclr
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The dotnetclr check is compatible with all major platforms


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information

# Agent Check: Boundary

## Overview

This check monitors [Boundary][1] through the Datadog Agent. The minimum supported version of Boundary is `0.8.0`.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Boundary check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

#### Listener

A listener with an `ops` purpose must be set up in the `config.hcl` file to enable metrics collection. Here's an example listener stanza:

```hcl
controller {
  name = "boundary-controller"
  database {
    url = "postgresql://<username>:<password>@10.0.0.1:5432/<database_name>"
  }
}

listener "tcp" {
  purpose = "api"
  tls_disable = true
}

listener "tcp" {
  purpose = "ops"
  tls_disable = true
}
```

The `boundary.controller.health` [service check](#service-checks) submits as `WARNING` when the controller is shutting down. To enable this shutdown grace period, update the `controller` block with a defined wait duration:

```hcl
controller {
  name = "boundary-controller"
  database {
    url = "env://BOUNDARY_PG_URL"
  }
  graceful_shutdown_wait_duration = "10s"
}
```

#### Datadog Agent

1. Edit the `boundary.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your boundary performance data. See the [sample boundary.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `boundary` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Boundary integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. To start collecting your Boundary logs, add this configuration block to your `boundary.d/conf.yaml` file:

    ```yaml
    logs:
       - type: file
         source: boundary
         path: /var/log/boundary/events.ndjson
    ```

    Change the `path` parameter value based on your environment. See the [sample `boundary.d/conf.yaml` file][4] for all available configuration options.

## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://www.boundaryproject.io
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/boundary/datadog_checks/boundary/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/boundary/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/boundary/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/

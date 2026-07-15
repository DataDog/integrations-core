## Overview

> **Note:** This integration is in beta. Features and configuration options may change.

The Cloud Spanner integration collects [Database Monitoring][1] (DBM) query metrics from [Google Cloud Spanner][2]. DBM provides deep visibility into query performance, execution plans, and database health across all your Spanner databases.

When DBM is enabled, the integration queries `SPANNER_SYS.QUERY_STATS_TOP_MINUTE` and forwards normalized query metrics to Datadog.

## Setup

### Prerequisites

- A Google Cloud service account with the `spanner.databases.select` permission, or Application Default Credentials (ADC) when running inside GCP

### Installation

The Cloud Spanner check is included in the [Datadog Agent][3] package.

### Configuration

1. Edit the `cloud_spanner.d/conf.yaml` file in your Agent's `conf.d/` directory. See the [sample conf.yaml.example][4] for all available configuration options.

2. Minimal configuration:

   ```yaml
   instances:
     - project_id: my-gcp-project
       instance_id: my-spanner-instance
       database: my-database
       dbm: true
       credentials_path: /path/to/service-account-key.json
   ```

3. [Restart the Agent][5].

### Validation

Run `datadog-agent check cloud_spanner` to verify the configuration.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Service Checks

The Cloud Spanner integration does not include any service checks.

### Events

The Cloud Spanner integration does not include any events.

## Support

Need help? Contact [Datadog support][7].

[1]: https://docs.datadoghq.com/database_monitoring/
[2]: https://cloud.google.com/spanner
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://github.com/DataDog/integrations-core/blob/master/cloud_spanner/datadog_checks/cloud_spanner/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://github.com/DataDog/integrations-core/blob/master/cloud_spanner/metadata.csv
[7]: https://docs.datadoghq.com/help/

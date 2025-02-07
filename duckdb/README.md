# Agent Check: DuckDB

## Overview

DuckDB is a high-performance analytical database system. It is available as a standalone CLI application and has clients for Python, R, Java, Wasm, etc., with deep integrations with packages such as pandas and dplyr.

For more information on using DuckDB, refer to the [DuckDB documentation][9].

This check monitors [DuckDB][1] through the Datadog Agent. 

## Setup

DuckDB has two configurable options for concurrency:

- One process can both read and write to the database.
- Multiple processes can read from the database, but no processes can write (access_mode = 'READ_ONLY').

<div class="alert alert-warning">
The Datadog Agent uses the <code>read_only</code> mode to get metrics, with a default frequency of 60 seconds (<code>min_collection_interval</code>). 
You can increase this value to reduce concurrency issues.
</div>

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The DuckDB check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

#### Dependencies

The [duckdb][10] client library is required. To install it, ensure you have a working compiler and run:

##### Unix

```text
sudo -Hu dd-agent /opt/datadog-agent/embedded/bin/pip install duckdb==1.1.1
```
##### Windows

```text
"C:\Program Files\Datadog\Datadog Agent\embedded3\python.exe" -m pip install duckdb==1.1.1
```

### Configuration

1. Edit the `duckdb.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your duckdb performance data. See the [sample duckdb.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `duckdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The DuckDB integration does not include any events.

### Service Checks

The DuckDB integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][8].


[1]: https://docs.datadoghq.com/integrations/duckdb/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/duckdb/datadog_checks/duckdb/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/duckdb/metadata.csv
[8]: https://docs.datadoghq.com/help/
[9]: https://duckdb.org/docs/
[10]: https://pypi.org/project/duckdb/

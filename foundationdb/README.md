# Agent Check: FoundationDB

## Overview

This check monitors [FoundationDB][1] through the Datadog Agent. Aside from
checking that the FoundationDB cluster is healthy, it also collects numerous metrics
and, optionally, FoundationDB transaction logs.

## Setup

Both the check and metrics apply to the FoundationDB cluster as a whole,
and should only be installed on one host. The host doesn't need to be one that is
running FoundationDB, but just one with access to it.

### Installation

The FoundationDB check is included in the [Datadog Agent][2] package,
but requires the [FoundationDB client][8] to be installed.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. To start collecting your FoundationDB metrics, edit the `foundationdb.d/conf.yaml` file in the `conf.d/` folder at the root of your Agent's configuration directory.
   See the [sample foundationdb.d/conf.yaml][3] for all available configuration options.

2. The cluster to check is determined by searching for a cluster file  in the [default location][10]. If the cluster file is located elsewhere,
set the `cluster_file` property. Only one cluster can be monitored per check instance.

3. If the cluster is [configured to use TLS][1], further properties should  be set in the configuration. These properties follow the names of the TLS
related options given to `fdbcli` to connect to such a cluster.

4. [Restart the Agent][4].

##### Log collection

FoundationDB writes XML logs by default, however, Datadog integrations expect JSON logs. Thus, a configuration change needs to be made to
FoundationDB.

1. Locate your `foundationdb.conf` file. Under the `fdbserver` section, add
   or change the key `trace_format` to have the value `json`. Also, make
   note of the `logdir`.

    ```
    [fdbserver]
    ...
    logdir = /var/log/foundationdb
    trace_format = json
    ```

2. Restart the FoundationDB server so the changes take effect. Verify that
   logs in the `logdir` are written in JSON.

3. Ensure that log collection is enabled in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

4. In the `foundationdb.d/conf.yaml` file, uncomment the `logs` section
   and set the path to the one in your FoundationDB configuration file,
   appending `*.json`.

    ```yaml
    logs:
      - type: file
        path: /var/log/foundationdb/*.json
        service: foundationdb
        source: foundationdb
    ```

5. Make sure the Datadog Agent has the privileges required to list the
   directory and read its files.

5. Restart the Datadog Agent.

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][12] for guidance on applying the parameters below.


##### Metric collection

| Parameter            | Value                                                      |
|----------------------|------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `foundationdb`                                             |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{}`                                                       |

##### Log collection

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes log collection][13].

| Parameter      | Value                                     |
|----------------|-------------------------------------------|
| `<LOG_CONFIG>` | `{"source": "foundationdb", "service": "<SERVICE_NAME>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->


### Validation

[Run the Agent's status subcommand][5] and look for `foundationdb` under the **Checks** section.


## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

### Events

The FoundationDB check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.foundationdb.org/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/integrations-core/blob/master/foundationdb/datadog_checks/foundationdb/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/foundationdb/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://apple.github.io/foundationdb/downloads.html
[9]: https://app.datadoghq.com/account/settings/agent/latest
[10]: https://apple.github.io/foundationdb/administration.html#default-cluster-file
[11]: https://apple.github.io/foundationdb/tls.html
[12]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[13]: https://docs.datadoghq.com/agent/kubernetes/log/
[14]: https://github.com/DataDog/integrations-core/blob/master/foundationdb/assets/service_checks.json

# Agent Check: ProxySQL

## Overview

This check monitors [ProxySQL][1] through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

To install the ProxySQL check on your host:

1. Install the [developer toolkit][8] on any machine.
2. Run `ddev release build proxysql` to build the package.
3. [Download the Datadog Agent][9].
4. Upload the build artifact to any host with an Agent and run `datadog-agent integration install -w path/to/proxysql/dist/<ARTIFACT_NAME>.whl`.

### Configuration

1. Edit the `proxysql.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your ProxySQL performance data. See the [sample proxysql.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4].

### Validation

[Run the Agent's status subcommand][5] and look for `proxysql` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

The ProxySQL check tags all collected service checks with:

- `server:<SERVER_IN_YAML>`
- `port:<PORT_IN_YAML>`
- Any extra tagd in the `tags` configuration

**proxysql.can_connect**:<br>
Returns `CRITICAL` if the Agent can't connect to ProxySQL, `OK` otherwise.

### Events

The ProxySQL check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://proxysql.com/
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://github.com/DataDog/integrations-core/blob/master/proxysql/datadog_checks/proxysql/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/proxysql/metadata.csv
[7]: https://docs.datadoghq.com/help
[8]: https://docs.datadoghq.com/developers/integrations/new_check_howto/#developer-toolkit
[9]: https://app.datadoghq.com/account/settings#agent

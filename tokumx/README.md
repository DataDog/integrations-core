# Agent Check: TokuMX

## Overview

This check collects TokuMX metrics, including:

- Opcounters.
- Replication lag.
- Cache table utilization and storage size.

## Setup

### Installation

The TokuMX check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your TokuMX servers.

### Configuration

#### Prepare TokuMX

1. Install the Python MongoDB module on your MongoDB server using the following command:

   ```shell
   sudo pip install --upgrade "pymongo<3.0"
   ```

2. You can verify that the module is installed using this command:

   ```shell
   python -c "import pymongo" 2>&1 | grep ImportError && \
   echo -e "\033[0;31mpymongo python module - Missing\033[0m" || \
   echo -e "\033[0;32mpymongo python module - OK\033[0m"
   ```

3. Start the Mongo shell. In the shell, create a read-only user for the Datadog Agent in the `admin` database:

   ```shell
   # Authenticate as the admin user.
   use admin
   db.auth("admin", "<YOUR_TOKUMX_ADMIN_PASSWORD>")
   # Add a user for Datadog Agent
   db.addUser("datadog", "<UNIQUEPASSWORD>", true)
   ```

4. Verify that you created the user with the following command (not in the Mongo shell).

   ```shell
   python -c 'from pymongo import Connection; print Connection().admin.authenticate("datadog", "<UNIQUEPASSWORD>")' | \
   grep True && \
   echo -e "\033[0;32mdatadog user - OK\033[0m" || \
   echo -e "\033[0;31mdatadog user - Missing\033[0m"
   ```

For more details about creating and managing users in MongoDB, see [the MongoDB documentation][3].

#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `tokumx.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][4].
   See the [sample tokumx.d/conf.yaml][5] for all available configuration options:

   ```yaml
   init_config:

   instances:
     - server: "mongodb://<USER>:<PASSWORD>@localhost:27017"
   ```

2. [Restart the Agent][6] to start sending TokuMX metrics to Datadog.

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

| Parameter            | Value                                                      |
| -------------------- | ---------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `tokumx`                                                   |
| `<INIT_CONFIG>`      | blank or `{}`                                              |
| `<INSTANCE_CONFIG>`  | `{"server": "mongodb://<USER>:<PASSWORD>@%%host%%:27017"}` |

### Validation

[Run the Agent's `status` subcommand][7] and look for `tokumx` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Events

**Replication state changes**:

This check emits an event each time a TokuMX node has a change in its replication state.

### Service Checks

`tokumx.can_connect`:

Returns CRITICAL if the Agent cannot connect to TokuMX to collect metrics, otherwise OK.

## Troubleshooting

Need help? Contact [Datadog support][9].

## Further Reading

- [Monitor key TokuMX metrics for MongoDB applications][10].

[1]: https://docs.datadoghq.com/agent/kubernetes/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://www.mongodb.org/display/DOCS/Security+and+Authentication
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/tokumx/datadog_checks/tokumx/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/tokumx/metadata.csv
[9]: https://docs.datadoghq.com/help
[10]: https://www.datadoghq.com/blog/monitor-key-tokumx-metrics-mongodb-applications

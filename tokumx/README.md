# Agent Check: TokuMX

## Overview

This check collects TokuMX metrics like:

* Opcounters
* Replication lag
* Cache table utilization and storage size

And more.

## Setup
### Installation

The TokuMX check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your TokuMX servers.

If you need the newest version of the TokuMX check, install the `dd-check-tokumx` package; this package's check overrides the one packaged with the Agent. See the [Installing Core & Extra Integrations documentation page](https://docs.datadoghq.com/agent/faq/install-core-extra/) for more details.

### Configuration
#### Prepare TokuMX

1.  Install the Python MongoDB module on your MongoDB server using the following command:

        sudo pip install --upgrade "pymongo<3.0"


2.  You can verify that the module is installed using this command:

        python -c "import pymongo" 2>&1 | grep ImportError && \
        echo -e "\033[0;31mpymongo python module - Missing\033[0m" || \
        echo -e "\033[0;32mpymongo python module - OK\033[0m"


3.  Start the mongo shell.In it create a read-only user for the Datadog Agent in the `admin` database:

        # Authenticate as the admin user.
        use admin
        db.auth("admin", "<YOUR_TOKUMX_ADMIN_PASSWORD>")
        # Add a user for Datadog Agent
        db.addUser("datadog", "<UNIQUEPASSWORD>", true)


4.  Verify that you created the user with the following command (not in the mongo shell).

        python -c 'from pymongo import Connection; print Connection().admin.authenticate("datadog", "<UNIQUEPASSWORD>")' | \
        grep True && \
        echo -e "\033[0;32mdatadog user - OK\033[0m" || \
        echo -e "\033[0;31mdatadog user - Missing\033[0m"

For more details about creating and managing users in MongoDB, refer to [the MongoDB documentation](http://www.mongodb.org/display/DOCS/Security+and+Authentication).

#### Connect the Agent

Create a file `tokumx.yaml` in the Agent's `conf.d` directory. See the [sample tokumx.yaml](https://github.com/DataDog/integrations-core/blob/master/tokumx/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  - server: mongodb://datadog:<UNIQUEPASSWORD>@localhost:27017
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to start sending TokuMX metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `tokumx` under the Checks section:

```
  Checks
  ======
    [...]

    tokumx
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The tokumx check is compatible with all major platforms.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/tokumx/metadata.csv) for a list of metrics provided by this check.

### Events
**Replication state changes**:

This check emits an event each time a TokuMX node has a change in its replication state.

### Service Checks

`tokumx.can_connect`:

Returns CRITICAL if the Agent cannot connect to TokuMX to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

* [Monitor key TokuMX metrics for MongoDB applications](https://www.datadoghq.com/blog/monitor-key-tokumx-metrics-mongodb-applications/).

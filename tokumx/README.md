# Agent Check: TokuMX

## Overview

This check collects TokuMX metrics like:

* Opcounters
* Replication lag
* Cache table utilization and storage size

And more.

## Setup
### Installation

The TokuMX check is packaged with the Agent, so simply [install the Agent][1] on your TokuMX servers.

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

For more details about creating and managing users in MongoDB, refer to [the MongoDB documentation][2].

#### Connect the Agent

Create a file `tokumx.yaml` in the Agent's `conf.d` directory. See the [sample tokumx.yaml][3] for all available configuration options:

```
init_config:

instances:
  - server: mongodb://datadog:<UNIQUEPASSWORD>@localhost:27017
```

[Restart the Agent][4] to start sending TokuMX metrics to Datadog.

### Validation

[Run the Agent's `status` subcommand][5] and look for `tokumx` under the Checks section:

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
See [metadata.csv][6] for a list of metrics provided by this check.

### Events
**Replication state changes**:

This check emits an event each time a TokuMX node has a change in its replication state.

### Service Checks

`tokumx.can_connect`:

Returns CRITICAL if the Agent cannot connect to TokuMX to collect metrics, otherwise OK.

## Troubleshooting
Need help? Contact [Datadog Support][7].

## Further Reading

* [Monitor key TokuMX metrics for MongoDB applications][8].


[1]: https://app.datadoghq.com/account/settings#agent
[2]: http://www.mongodb.org/display/DOCS/Security+and+Authentication
[3]: https://github.com/DataDog/integrations-core/blob/master/tokumx/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/tokumx/metadata.csv
[7]: http://docs.datadoghq.com/help/
[8]: https://www.datadoghq.com/blog/monitor-key-tokumx-metrics-mongodb-applications/

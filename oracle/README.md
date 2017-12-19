# Oracle Integration

## Overview

Get metrics from Oracle Database servers in real time to visualize and monitor availability and performance.

## Setup
### Installation

Install the `dd-check-oracle` package manually or with your favorite configuration manager.

In order to use the Oracle integration you must install the Oracle Instant Client libraries. Due to licensing restrictions we are unable to include these libraries in our agent, but you can [download them directly frrom Oracle](https://www.oracle.com/technetwork/database/features/instant-client/index.htm).

You will need to install the Instant Client Basic and SDK packages.

After you have installed the Instant Client libraries, ensure that the runtime linker can find the libraries. For example, using `'ldconfig`:

```
# Put the library location in an ld configuration file.
sudo sh -c "echo /usr/lib/oracle/12.2/client64/lib > \
    /etc/ld.so.conf.d/oracle-instantclient.conf"

# Update the bindings.
sudo ldconfig
```

Alternately, you can update your `LD_LIBRARY_PATH` to include the location of the Instant Client libraries. For example:

```
mkdir -p /opt/oracle/ && cd /opt/oracle/

# Download Oracle Instant Client (example dir: /opt/oracle).
unzip /opt/oracle/instantclient-basic-linux.x64-12.1.0.2.0.zip
unzip /opt/oracle/instantclient-sdk-linux.x64-12.1.0.2.0.zip

export LD_LIBRARY_PATH=/opt/oracle/instantclient/lib:$LD_LIBRARY_PATH
```

Finally, you will need to create a read-only datadog user with proper access to your Oracle Database Server. Connect to your Oracle database with an administrative user (e.g. `SYSDBA` or `SYSOPER`) and run:

```
-- Enable Oracle Script.
ALTER SESSION SET "_ORACLE_SCRIPT"=true;

-- Create the datadog user. Replace the password placeholder with a secure password.
CREATE USER datadog IDENTIFIED BY <password>;

-- Grant access to the datadog user.
GRANT CONNECT TO datadog;
GRANT SELECT ON gv_$sysmetric TO datadog;
```

### Configuration

Edit the `oracle.yaml` file to point to your server and port, set the masters to monitor. See the [sample oracle.yaml](https://github.com/DataDog/integrations-core/blob/master/oracle/conf.yaml.example) for all available configuration options.

Configuration Options:
* **`server`** (Required) - The IP address or hostname of the Oracle Database server.
* **`service_name`** (Required) - The Oracle Database service name. To view the services available on your server, run the following query: `SELECT value FROM v$parameter WHERE name='service_names'`.
* **`user`** (Required) - If you followed [the instructions above](#installation), set this to the read-only user `datadog`. Otherwise set it to a user with sufficient privileges to connect to the database and read system metrics.
* **`password`** (Required) - The password for the user account.
* **`tags`** (Optional) - A list of tags applied to all metrics collected. Tags may be simple strings or key-value pairs.

### Validation

[Run the Agent's `info` subcommand](https://docs.datadoghq.com/agent/faq/agent-status-and-information/) and look for `oracle` under the Checks section:

    Checks
    ======

        oracle
        -----------
          - instance #0 [OK]
          - Collected 18 metrics, 0 events & 1 service checks

### Compatibility

The Oracle check is currently compatible with Linux and macOS.

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv) for a list of metrics provided by this integration.

### Events
The Oracle Database check does not include any events at this time.

### Service Checks
The Oracle Database integration includes the service check `oracle.can_connect` which will verify the database is available and accepting connections.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading

Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)

# Oracle Integration

![Oracle Dashboard][1]

## Overview

Get metrics from Oracle Database servers in real time to visualize and monitor availability and performance.

## Setup

### Installation

To use the Oracle integration, either install the Oracle Instant Client libraries, or download the Oracle JDBC Driver. Due to licensing restrictions, these libraries are not included in the Datadog Agent, but can be downloaded directly from Oracle.

#### Steps for the JDBC Driver

- [Download][2] the jar file.
- Add the path to the downloaded file in your `$CLASSPATH` or the check configuration file under `jdbc_driver_path` (see the [sample oracle.yaml][3]).

#### Steps for the Instant Client

Go to the [download page][4] and install the Instant Client Basic and SDK packages.

If you are using Linux, after the Instant Client libraries are installed ensure the runtime linker can find the libraries. For example, using `ldconfig`:

```
    # Put the library location in an ld configuration file.

sudo sh -c "echo /usr/lib/oracle/12.2/client64/lib > \
    /etc/ld.so.conf.d/oracle-instantclient.conf"

    # Update the bindings.

sudo ldconfig
```

Alternately, update your `LD_LIBRARY_PATH` to include the location of the Instant Client libraries. For example:

```
mkdir -p /opt/oracle/ && cd /opt/oracle/

    # Download Oracle Instant Client (example dir: /opt/oracle).

unzip /opt/oracle/instantclient-basic-linux.x64-12.1.0.2.0.zip
unzip /opt/oracle/instantclient-sdk-linux.x64-12.1.0.2.0.zip

export LD_LIBRARY_PATH=/opt/oracle/instantclient/lib:$LD_LIBRARY_PATH
```

**Note:** Agent 6 uses Upstart or systemd to orchestrate the `datadog-agent` service. Environment variables may need to be added to the service configuration files at the default locations of `/etc/init/datadog-agent.conf` (Upstart) or `/lib/systemd/system/datadog-agent.service` (systemd). See documentation on [Upstart][5] or [systemd][6] for more information on how to configure these settings.

The following is an example of adding `LD_LIBRARY_PATH` to the Datadog Agent service configuration files (`/int/init/datadog-agent.conf`) on a system using Upstart.

```
description "Datadog Agent"

start on started networking
stop on runlevel [!2345]

respawn
respawn limit 10 5
normal exit 0

# Logging to console from the Agent is disabled since the Agent already logs using file or
# syslog depending on its configuration. We make Upstart log what the process still outputs in order
# to log panics/crashes to /var/log/upstart/datadog-agent.log
console log
env DD_LOG_TO_CONSOLE=false
env LD_LIBRARY_PATH=/usr/lib/oracle/11.2/client64/lib/

setuid dd-agent

script
  exec /opt/datadog-agent/bin/agent/agent start -p /opt/datadog-agent/run/agent.pid
end script

post-stop script
  rm -f /opt/datadog-agent/run/agent.pid
end script
```

#### After installing either the JDBC Driver or the Instant Client

Create a read-only `datadog` user with proper access to your Oracle Database Server. Connect to your Oracle database with an administrative user (e.g. `SYSDBA` or `SYSOPER`) and run:

```
-- Enable Oracle Script.
ALTER SESSION SET "_ORACLE_SCRIPT"=true;

-- Create the datadog user. Replace the password placeholder with a secure password.
CREATE USER datadog IDENTIFIED BY <PASSWORD>;

-- Grant access to the datadog user.
GRANT CONNECT TO datadog;
GRANT SELECT ON GV_$PROCESS TO datadog;
GRANT SELECT ON gv_$sysmetric TO datadog;
GRANT SELECT ON sys.dba_data_files TO datadog;
```

**Note**: If you're using Oracle 11g, there's no need to run the following line:

```
ALTER SESSION SET "_ORACLE_SCRIPT"=true;
```

### Configuration

Edit the `oracle.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][7] to point to your server and port, set the masters to monitor. See the [sample oracle.d/conf.yaml][3] for all available configuration options.

Configuration Options:

| Option         | Required | Description                                                                                                                                                                                                                                                   |
|----------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `server`       | Yes      | The IP address or hostname of the Oracle Database Server.                                                                                                                                                                                                     |
| `service_name` | Yes      | The Oracle Database service name. To view the services available on your server, run the following query: `SELECT value FROM v$parameter WHERE name='service_names'`.                                                                                         |
| `user`         | Yes      | If you followed [the instructions above](#after-installing-either-the-jdbc-driver-or-the-instant-client), set this to the read-only user `datadog`. Otherwise set it to a user with sufficient privileges to connect to the database and read system metrics. |
| `password`     | Yes      | The password for the user account.                                                                                                                                                                                                                            |
| `tags`         | No       | A list of tags applied to all metrics collected. Tags may be simple strings or key-value pairs.                                                                                                                                                               |

### Validation

[Run the Agent's status subcommand][8] and look for `oracle` under the Checks section.

## Data Collected

### Metrics
See [metadata.csv][9] for a list of metrics provided by this integration.

### Events
The Oracle Database check does not include any events.

### Service Checks
**oracle.can_connect**  
Verifies the database is available and accepting connections.

## Troubleshooting
Need help? Contact [Datadog support][10].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/oracle/images/oracle_dashboard.png
[2]: https://www.oracle.com/technetwork/database/application-development/jdbc/downloads/index.html
[3]: https://github.com/DataDog/integrations-core/blob/master/oracle/datadog_checks/oracle/data/conf.yaml.example
[4]: https://www.oracle.com/technetwork/database/features/instant-client/index.htm
[5]: http://upstart.ubuntu.com/cookbook/#environment-variables
[6]: https://www.freedesktop.org/software/systemd/man/systemd.service.html#Command%20lines
[7]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
[8]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv
[10]: https://docs.datadoghq.com/help

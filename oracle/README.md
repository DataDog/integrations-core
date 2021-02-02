# Oracle Integration

![Oracle Dashboard][1]

## Overview

Get metrics from Oracle Database servers in real time to visualize and monitor availability and performance.

## Setup

### Installation

#### Prerequisite

To use the Oracle integration, either install the Oracle Instant Client libraries, or download the Oracle JDBC Driver. Due to licensing restrictions, these libraries are not included in the Datadog Agent, but can be downloaded directly from Oracle.

##### Oracle Instant Client

The Oracle check requires either access to the `cx_Oracle` Python module, or the Oracle JDBC Driver:

1. Go to the [download page][4] and install both the Instant Client Basic and SDK packages.

    If you are using Linux, after the Instant Client libraries are installed ensure the runtime linker can find the libraries. For example, using `ldconfig`:

   ```shell
   # Put the library location in an ld configuration file.

   sudo sh -c "echo /usr/lib/oracle/12.2/client64/lib > \
       /etc/ld.so.conf.d/oracle-instantclient.conf"

   # Update the bindings.

   sudo ldconfig
   ```

2. Decompress those libraries in a given directory available to all users on the given machine (i.e. `/opt/oracle`):

   ```shell
   mkdir -p /opt/oracle/ && cd /opt/oracle/
   unzip /opt/oracle/instantclient-basic-linux.x64-12.1.0.2.0.zip
   unzip /opt/oracle/instantclient-sdk-linux.x64-12.1.0.2.0.zip
   ```

##### JDBC Driver

The following runtimes are required on your system for JPype, one of the libraries used by the Agent when using JDBC Driver:

- Java 8 or higher 
- [Microsoft Visual C++ Runtime 2015][13] on windows.

Once these are installed, follow the following steps: 

1. [Download the JDBC Driver][2] jar file.
2. Add the path to the downloaded file in your `$CLASSPATH` or the check configuration file under `jdbc_driver_path` (see the [sample oracle.yaml][3]).

#### Datadog User creation

<!-- xxx tabs xxx -->
<!-- xxx tab "Stand Alone" xxx -->

Create a read-only `datadog` user with proper access to your Oracle Database Server. Connect to your Oracle database with an administrative user (e.g. `SYSDBA` or `SYSOPER`) and run:

```text
-- Enable Oracle Script.
ALTER SESSION SET "_ORACLE_SCRIPT"=true;

-- Create the datadog user. Replace the password placeholder with a secure password.
CREATE USER datadog IDENTIFIED BY <PASSWORD>;

-- Grant access to the datadog user.
GRANT CONNECT TO datadog;
GRANT SELECT ON GV_$PROCESS TO datadog;
GRANT SELECT ON gv_$sysmetric TO datadog;
GRANT SELECT ON sys.dba_data_files TO datadog;
GRANT SELECT ON sys.dba_tablespaces TO datadog;
GRANT SELECT ON sys.dba_tablespace_usage_metrics TO datadog;
```

**Note**: If you're using Oracle 11g, there's no need to run the following line:

```text
ALTER SESSION SET "_ORACLE_SCRIPT"=true;
```

<!-- xxz tab xxx -->
<!-- xxx tab "Multitenant" xxx -->

##### Oracle 12c or 19c

Log in to the root database as an Administrator to create a `datadog` user and grant permissions:

```text
alter session set container = cdb$root;
CREATE USER c##datadog IDENTIFIED BY password CONTAINER=ALL;
GRANT CREATE SESSION TO c##datadog CONTAINER=ALL;
Grant select any dictionary to c##datadog container=all;
GRANT SELECT ON GV_$PROCESS TO c##datadog CONTAINER=ALL;
GRANT SELECT ON gv_$sysmetric TO c##datadog CONTAINER=ALL;
```

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

1. Edit the `oracle.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][7]. Update the `server` and `port` to set the masters to monitor. See the [sample oracle.d/conf.yaml][3] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param server - string - required
     ## The IP address or hostname of the Oracle Database Server.
     #
     - server: localhost:1521

       ## @param service_name - string - required
       ## The Oracle Database service name. To view the services available on your server,
       ## run the following query:
       ## `SELECT value FROM v$parameter WHERE name='service_names'`
       #
       service_name: "<SERVICE_NAME>"

       ## @param user - string - required
       ## The username for the user account.
       #
       user: datadog

       ## @param password - string - required
       ## The password for the user account.
       #
       password: "<PASSWORD>"
   ```

2. [Restart the Agent][8].

#### Only custom queries

To skip default metric checks for an instance and only run custom queries with an existing metrics gathering user, insert the tag `only_custom_queries` with a value of true. This allows a configured instance of the Oracle integration to skip the system, process, and tablespace metrics from running, and allows custom queries to be run without having the permissions described in the [Datadog user creation](#datadog-user-creation) section. If this configuration entry is omitted, the user you specify is required to have those table permissions to run a custom query.

```yaml
init_config:

instances:
  ## @param server - string - required
  ## The IP address or hostname of the Oracle Database Server.
  #
  - server: localhost:1521

    ## @param service_name - string - required
    ## The Oracle Database service name. To view the services available on your server,
    ## run the following query:
    ## `SELECT value FROM v$parameter WHERE name='service_names'`
    #
    service_name: "<SERVICE_NAME>"

    ## @param user - string - required
    ## The username for the user account.
    #
    user: <USER>

    ## @param password - string - required
    ## The password for the user account.
    #
    password: "<PASSWORD>"

    ## @param only_custom_queries - string - optional
    ## Set this parameter to any value if you want to only run custom
    ## queries for this instance.
    #
    only_custom_queries: true
```

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][9] for guidance on applying the parameters below.

| Parameter            | Value                                                                                                     |
| -------------------- | --------------------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `oracle`                                                                                                  |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                             |
| `<INSTANCE_CONFIG>`  | `{"server": "%%host%%:1521", "service_name":"<SERVICE_NAME>", "user":"datadog", "password":"<PASSWORD>"}` |

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][10] and look for `oracle` under the Checks section.

## Custom Query

Providing custom queries is also supported. Each query must have 3 parameters:

| Parameter       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `metric_prefix` | This is what each metric starts with.                                                                                                                                                                                                                                                                                                                                                                                                         |
| `query`         | This is the SQL to execute. It can be a simple statement or a multi-line script. All rows of the result are evaluated.                                                                                                                                                                                                                                                                                                                        |
| `columns`       | This is a list representing each column, ordered sequentially from left to right. There are 2 required pieces of data: <br> a. `type` - This is the submission method (`gauge`, `count`, etc.). <br> b. name - This is the suffix to append to the `metric_prefix` in order to form the full metric name. If `type` is `tag`, this column is instead considered as a tag which is applied to every metric collected by this particular query. |

Optionally use the `tags` parameter to apply a list of tags to each metric collected.

The following:

```python
self.gauge('oracle.custom_query.metric1', value, tags=['tester:oracle', 'tag1:value'])
self.count('oracle.custom_query.metric2', value, tags=['tester:oracle', 'tag1:value'])
```

is what the following example configuration would become:

```yaml
- metric_prefix: oracle.custom_query
  query: | # Use the pipe if you require a multi-line script.
    SELECT columns
    FROM tester.test_table
    WHERE conditions
  columns:
    # Put this for any column you wish to skip:
    - {}
    - name: metric1
      type: gauge
    - name: tag1
      type: tag
    - name: metric2
      type: count
  tags:
    - tester:oracle
```

See the [sample oracle.d/conf.yaml][3] for all available configuration options.

### Example

Create a query configuration to help identify database locks:

1. To include a custom query, modify `conf.d\oracle.d\conf.yaml`. Uncomment the `custom_queries` block, add the required queries and columns, and restart the agent.

```yaml
  init_config:
  instances:
      - server: localhost:1521
        service_name: orcl11g.us.oracle.com
        user: datadog
        password: xxxxxxx
        jdbc_driver_path: /u01/app/oracle/product/11.2/dbhome_1/jdbc/lib/ojdbc6.jar
        tags:
          - db:oracle
        custom_queries:
          - metric_prefix: oracle.custom_query.locks
            query: |
              select blocking_session, username, osuser, sid, serial# as serial, wait_class, seconds_in_wait
              from v_$session
              where blocking_session is not NULL order by blocking_session
            columns:
              - name: blocking_session
                type: gauge
              - name: username
                type: tag
              - name: osuser
                type: tag
              - name: sid
                type: tag
              - name: serial
                type: tag
              - name: wait_class
                type: tag
              - name: seconds_in_wait
                type: tag
```

2. To access `v_$session`, give permission to `DATADOG` and test the permissions.

```text
SQL> grant select on sys.v_$session to datadog;

##connecting with the DD user to validate the access:


SQL> show user
USER is "DATADOG"


##creating a synonym to make the view visible
SQL> create synonym datadog.v_$session for sys.v_$session;


Synonym created.


SQL> select blocking_session,username,osuser, sid, serial#, wait_class, seconds_in_wait from v_$session
where blocking_session is not NULL order by blocking_session;
```

3. Once configured, you can create a [monitor][14] based on `oracle.custom_query.locks` metrics.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Events

The Oracle Database check does not include any events.

### Service Checks

**oracle.can_connect**:<br>
Verifies the database is available and accepting connections.

## Troubleshooting

Need help? Contact [Datadog support][12].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/oracle/images/oracle_dashboard.png
[2]: https://www.oracle.com/technetwork/database/application-development/jdbc/downloads/index.html
[3]: https://github.com/DataDog/integrations-core/blob/master/oracle/datadog_checks/oracle/data/conf.yaml.example
[4]: https://www.oracle.com/technetwork/database/features/instant-client/index.htm
[5]: http://upstart.ubuntu.com/cookbook/#environment-variables
[6]: https://www.freedesktop.org/software/systemd/man/systemd.service.html#Command%20lines
[7]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[9]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[10]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[11]: https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv
[12]: https://docs.datadoghq.com/help/
[13]: https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads
[14]: https://docs.datadoghq.com/monitors/monitor_types/metric/?tab=threshold

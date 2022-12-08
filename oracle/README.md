# Oracle Integration

![Oracle Dashboard][1]

## Overview

Get metrics from Oracle Database servers in real time to visualize and monitor availability and performance.

## Setup

### Installation

#### Prerequisite

To use the Oracle integration you can either use the native client (no additional install steps required) or download the Oracle JDBC driver (Linux only). To use the Oracle integration with JDBC, download the Oracle JDBC driver. If not using the JDBC method, the minimun [supported version][2] is Oracle 12c.
Due to licensing restrictions, the JDBC library is not included in the Datadog Agent, but can be downloaded directly from Oracle.

With Agent v7.42.x, the Agent no longer requires or supports installing the Instant Client libraries. If you're on an older version of the Agent and want to use the Instant Client, refer to the [Oracle Instant Client][3] setup instructions.

*NOTE*: Starting in v7.42.x, the Oracle integration only supports Python 3.


##### JDBC driver

*NOTE*: This method only works on Linux.

Java 8 or higher is required on your system for JPype, one of the libraries used by the Agent when using JDBC driver.

Once it is installed, complete the following steps: 

1. [Download the JDBC Driver][4] JAR file.
2. Add the path to the downloaded file in your `$CLASSPATH` or the check configuration file under `jdbc_driver_path` (see the [sample oracle.yaml][5]).

#### Datadog user creation

<!-- xxx tabs xxx -->
<!-- xxx tab "Stand Alone" xxx -->

Create a read-only `datadog` user with proper access to your Oracle Database Server. Connect to your Oracle database with an administrative user, such as `SYSDBA` or `SYSOPER`, and run:

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

1. Edit the `oracle.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][6]. Update the `server` and `port` to set the masters to monitor. See the [sample oracle.d/conf.yaml][5] for all available configuration options.

   ```yaml
   init_config:

   instances:
     ## @param server - string - required
     ## The IP address or hostname of the Oracle Database Server.
     #
     - server: localhost:1521

      ## @param service_name - string - required
      ## The Oracle Database service name. To view the services available on your server,
      ## run the following query: `SELECT value FROM v$parameter WHERE name='service_names'`
      #
      service_name: <SERVICE_NAME>

      ## @param username - string - required
      ## The username for the Datadog user account.
      #
      username: <USERNAME>

      ## @param password - string - required
      ## The password for the Datadog user account.
      #
      password: <PASSWORD>
   ```

2. [Restart the Agent][7].


#### Only custom queries

To skip default metric checks for an instance and only run custom queries with an existing metrics gathering user, insert the tag `only_custom_queries` with a value of `true`. This allows a configured instance of the Oracle integration to skip the system, process, and tablespace metrics from running, and allows custom queries to be run without having the permissions described in the [Datadog user creation](#datadog-user-creation) section. If this configuration entry is omitted, the user you specify is required to have those table permissions to run a custom query.

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

#### Connect to Oracle through TCPS

1. To connect to Oracle through TCPS (TCP with SSL), uncomment the `protocol` configuration option and select `TCPS`. Update the `server` option to set the TCPS server to monitor.

    ```yaml
    init_config:
    
    instances:
      ## @param server - string - required
      ## The IP address or hostname of the Oracle Database Server.
      #
      - server: localhost:1522
    
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
    
        ## @param protocol - string - optional - default: TCP
        ## The protocol to connect to the Oracle Database Server. Valid protocols include TCP and TCPS.
        ##
        ## When connecting to Oracle Database via JDBC, `jdbc_truststore` and `jdbc_truststore_type` are required.
        ## More information can be found from Oracle Database's whitepaper:
        ##
        ## https://www.oracle.com/technetwork/topics/wp-oracle-jdbc-thin-ssl-130128.pdf
        #
        protocol: TCPS
    ```

2. Update the `sqlnet.ora`, `listener.ora`, and `tnsnames.ora` to allow TCPS connections on your Oracle Database. 

##### TCPS through Oracle without JDBC

If you are not using JDBC, verify that the Datadog Agent is able to connect to your database. Use the `sqlplus` command line tool with the information inputted in your configuration options:

```shell
sqlplus <USER>/<PASSWORD>@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCPS)(HOST=<HOST>)(PORT=<PORT>))(SERVICE_NAME=<SERVICE_NAME>)))
```

##### TCPS through JDBC

If you are connecting to Oracle Database using JDBC, you also need to specify `jdbc_truststore_path`, `jdbc_truststore_type`, and `jdbc_truststore_password` (optional) if there is a password on the truststore. 

**Note**: `SSO` truststores don't require passwords.

```yaml
    # In the `instances:` section
    ...

    ## @param jdbc_truststore_path - string - optional
    ## The JDBC truststore file path.
    #
    jdbc_truststore_path: /path/to/truststore

    ## @param jdbc_truststore_type - string - optional
    ## The JDBC truststore file type. Supported truststore types include JKS, SSO, and PKCS12.
    #
    jdbc_truststore_type: SSO

    ## @param jdbc_truststore_password - string - optional
    ## The password for the truststore when connecting via JDBC.
    #
    # jdbc_truststore_password: <JDBC_TRUSTSTORE_PASSWORD>
```

For more information about connecting to the Oracle Database through TCPS on JDBC, see the official [Oracle whitepaper][15].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][8] for guidance on applying the parameters below.

| Parameter            | Value                                                                                                     |
| -------------------- | --------------------------------------------------------------------------------------------------------- |
| `<INTEGRATION_NAME>` | `oracle`                                                                                                  |
| `<INIT_CONFIG>`      | blank or `{}`                                                                                             |
| `<INSTANCE_CONFIG>`  | `{"server": "%%host%%:1521", "service_name":"<SERVICE_NAME>", "username":"datadog", "password":"<PASSWORD>"}` |


<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][9] and look for `oracle` under the Checks section.

## Custom query

Providing custom queries is also supported. Each query must have three parameters:

| Parameter       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `metric_prefix` | This is what each metric starts with.                                                                                                                                                                                                                                                                                                                                                                                                         |
| `query`         | This is the SQL to execute. It can be a simple statement or a multi-line script. All rows of the result are evaluated.                                                                                                                                                                                                                                                                                                                        |
| `columns`       | This is a list representing each column, ordered sequentially from left to right. There are two required pieces of data: <br> a. `type` - This is the submission method (`gauge`, `count`, etc.). <br> b. name - This is the suffix to append to the `metric_prefix` in order to form the full metric name. If `type` is `tag`, this column is instead considered as a tag which is applied to every metric collected by this particular query. |

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

See the [sample oracle.d/conf.yaml][5] for all available configuration options.

### Example

Create a query configuration to help identify database locks:

1. To include a custom query, modify `conf.d\oracle.d\conf.yaml`. Uncomment the `custom_queries` block, add the required queries and columns, and restart the Agent.

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

3. Once configured, you can create a [monitor][10] based on `oracle.custom_query.locks` metrics.

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Events

The Oracle Database check does not include any events.

### Service Checks

See [service_checks.json][12] for a list of service checks provided by this integration.

## Troubleshooting

### JDBC driver (Linux only)
- If you encounter a `JVMNotFoundException`:

    ```text
    JVMNotFoundException("No JVM shared library file ({jpype._jvmfinder.JVMNotFoundException: No JVM shared library file (libjvm.so) found. Try setting up the JAVA_HOME environment variable properly.})"
    ```

    - Ensure that the `JAVA_HOME` environment variable is set and pointing to the correct directory.
    - Add the environment variable to `/etc/environment`:
        ```text
        JAVA_HOME=/path/to/java
        ```
    - Then restart the Agent.

- If you encounter this error `Unsupported major.minor version 52.0` it means that you're running a Java version that
is too old. You need to either update your system Java or additionally install a newer version and point your `JAVA_HOME`
variable to the new install as explained above.

- Verify your environment variables are set correctly by running the following command from the Agent.
Ensure the displayed output matches the correct value.

    ```shell script
      sudo -u dd-agent -- /opt/datadog-agent/embedded/bin/python -c "import os; print(\"JAVA_HOME:{}\".format(os.environ.get(\"JAVA_HOME\")))"
    ```

Need help? Contact [Datadog support][14].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/oracle/images/oracle_dashboard.png
[2]: https://oracle.github.io/python-oracledb/
[3]: https://github.com/DataDog/integrations-core/tree/7.41.x/oracle#oracle-instant-client
[4]: https://www.oracle.com/technetwork/database/application-development/jdbc/downloads/index.html
[5]: https://github.com/DataDog/integrations-core/blob/master/oracle/datadog_checks/oracle/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://docs.datadoghq.com/monitors/monitor_types/metric/?tab=threshold
[11]: https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv
[12]: https://github.com/DataDog/integrations-core/blob/master/oracle/assets/service_checks.json
[13]: https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html
[14]: https://docs.datadoghq.com/help/
[15]: https://www.oracle.com/technetwork/topics/wp-oracle-jdbc-thin-ssl-130128.pdf
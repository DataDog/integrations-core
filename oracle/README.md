# Oracle Integration

![Oracle Dashboard][1]

## Overview

The Oracle integration provides health and performance metrics for your Oracle database in near real-time. Visualize these metrics with the provided dashboard and create monitors to alert your team on Oracle database states.

Enable [Database Monitoring][2] (DBM) for enhanced insights into query performance and database health. In addition to the standard integration features, Datadog DBM provides query-level metrics, live and historical query snapshots, wait event analysis, database load, query explain plans, and blocking query insights.


## Setup

### Installation

#### Prerequisite

To use the Oracle integration you can either use the native client (no additional install steps required), or the Oracle Instant Client.

##### Oracle Instant Client

Skip this step if you are not using Instant Client.

<!-- xxx tabs xxx -->

<!-- xxx tab "Linux" xxx -->
###### Linux

1. Follow the [Oracle Instant Client installation for Linux][15].

2. Verify that the *Instant Client Basic* package is installed. Find it on Oracle's [download page][8].

    After the Instant Client libraries are installed, ensure the runtime linker can find the libraries, for example:
    
      ```shell
      # Put the library location in the /etc/datadog-agent/environment file.

      echo "LD_LIBRARY_PATH=/u01/app/oracle/product/instantclient_19" \
      >> /etc/datadog-agent/environment
      ```

<!-- xxz tab xxx -->

<!-- xxx tab "Windows" xxx -->
###### Windows

1. Follow the [Oracle Windows installation guide][4] to configure your Oracle Instant Client.

2. Verify the following:
    - The [Microsoft Visual Studio 2017 Redistributable][3] or the appropriate version is installed for the Oracle Instant Client.

    - The *Instant Client Basic* package from Oracle's [download page][8] is installed, and is available to all users on the given machine (for example, `C:\oracle\instantclient_19`).

    - The `PATH` environment variable contains the directory with the Instant Client (for example, `C:\oracle\instantclient_19`).


<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Datadog user creation

<!-- xxx tabs xxx -->
<!-- xxx tab "Multi-tenant" xxx -->
##### Multi-tenant

###### Create user

Create a read-only login to connect to your server and grant the required permissions:

```SQL
CREATE USER c##datadog IDENTIFIED BY &password CONTAINER = ALL ;

ALTER USER c##datadog SET CONTAINER_DATA=ALL CONTAINER=CURRENT;
```

###### Grant permissions

Log on as `sysdba`, and grant the following permissions:

```SQL
grant create session to c##datadog ;
grant select on v_$session to c##datadog ;
grant select on v_$database to c##datadog ;
grant select on v_$containers to c##datadog;
grant select on v_$sqlstats to c##datadog ;
grant select on v_$instance to c##datadog ;
grant select on dba_feature_usage_statistics to c##datadog ;
grant select on V_$SQL_PLAN_STATISTICS_ALL to c##datadog ;
grant select on V_$PROCESS to c##datadog ;
grant select on V_$SESSION to c##datadog ;
grant select on V_$CON_SYSMETRIC to c##datadog ;
grant select on CDB_TABLESPACE_USAGE_METRICS to c##datadog ;
grant select on CDB_TABLESPACES to c##datadog ;
grant select on V_$SQLCOMMAND to c##datadog ;
grant select on V_$DATAFILE to c##datadog ;
grant select on V_$SYSMETRIC to c##datadog ;
grant select on V_$SGAINFO to c##datadog ;
grant select on V_$PDBS to c##datadog ;
grant select on CDB_SERVICES to c##datadog ;
grant select on V_$OSSTAT to c##datadog ;
grant select on V_$PARAMETER to c##datadog ;
grant select on V_$SQLSTATS to c##datadog ;
grant select on V_$CONTAINERS to c##datadog ;
grant select on V_$SQL_PLAN_STATISTICS_ALL to c##datadog ;
grant select on V_$SQL to c##datadog ;
grant select on V_$PGASTAT to c##datadog ;
grant select on v_$asm_diskgroup to c##datadog ;
grant select on v_$rsrcmgrmetric to c##datadog ;
grant select on v_$dataguard_config to c##datadog ;
grant select on v_$dataguard_stats to c##datadog ;
grant select on v_$transaction to c##datadog;
grant select on v_$locked_object to c##datadog;
grant select on dba_objects to c##datadog;
grant select on cdb_data_files to c##datadog;
grant select on dba_data_files to c##datadog;
```

If you configured custom queries that run on a pluggable database (PDB), you must grant the `set container` privilege to the `C##DATADOG` user:

```SQL
connect / as sysdba
alter session set container = your_pdb ;
grant set container to c##datadog ;
```

<!-- xxz tab xxx -->

<!-- xxx tab "Non-CDB" xxx -->
##### Non-CDB

###### Create user

Create a read-only login to connect to your server and grant the required permissions:

```SQL
CREATE USER datadog IDENTIFIED BY &password ;
```

###### Grant permissions

Log on as `sysdba`, and grant the following permissions:

```SQL
grant create session to datadog ;
grant select on v_$session to datadog ;
grant select on v_$database to datadog ;
grant select on v_$containers to datadog;
grant select on v_$sqlstats to datadog ;
grant select on v_$instance to datadog ;
grant select on dba_feature_usage_statistics to datadog ;
grant select on V_$SQL_PLAN_STATISTICS_ALL to datadog ;
grant select on V_$PROCESS to datadog ;
grant select on V_$SESSION to datadog ;
grant select on V_$CON_SYSMETRIC to datadog ;
grant select on CDB_TABLESPACE_USAGE_METRICS to datadog ;
grant select on CDB_TABLESPACES to datadog ;
grant select on V_$SQLCOMMAND to datadog ;
grant select on V_$DATAFILE to datadog ;
grant select on V_$SYSMETRIC to datadog ;
grant select on V_$SGAINFO to datadog ;
grant select on V_$PDBS to datadog ;
grant select on CDB_SERVICES to datadog ;
grant select on V_$OSSTAT to datadog ;
grant select on V_$PARAMETER to datadog ;
grant select on V_$SQLSTATS to datadog ;
grant select on V_$CONTAINERS to datadog ;
grant select on V_$SQL_PLAN_STATISTICS_ALL to datadog ;
grant select on V_$SQL to datadog ;
grant select on V_$PGASTAT to datadog ;
grant select on v_$asm_diskgroup to datadog ;
grant select on v_$rsrcmgrmetric to datadog ;
grant select on v_$dataguard_config to datadog ;
grant select on v_$dataguard_stats to datadog ;
grant select on v_$transaction to datadog;
grant select on v_$locked_object to datadog;
grant select on dba_objects to datadog;
grant select on cdb_data_files to datadog;
grant select on dba_data_files to datadog;
```

<!-- xxz tab xxx -->

<!-- xxx tab "RDS" xxx -->
##### RDS

###### Create user

Create a read-only login to connect to your server and grant the required permissions:

```SQL
CREATE USER datadog IDENTIFIED BY your_password ;
```

###### Grant permissions 

```SQL
grant create session to datadog ;
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SESSION','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$DATABASE','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$CONTAINERS','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SQLSTATS','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SQL','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$INSTANCE','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SQL_PLAN_STATISTICS_ALL','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('DBA_FEATURE_USAGE_STATISTICS','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$PROCESS','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SESSION','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$CON_SYSMETRIC','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('CDB_TABLESPACE_USAGE_METRICS','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('CDB_TABLESPACES','DATADOG','SELECT',p_grant_option => false); 
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SQLCOMMAND','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$DATAFILE','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SGAINFO','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SYSMETRIC','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$PDBS','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('CDB_SERVICES','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$OSSTAT','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$PARAMETER','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SQLSTATS','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$CONTAINERS','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SQL_PLAN_STATISTICS_ALL','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$SQL','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$PGASTAT','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$ASM_DISKGROUP','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$RSRCMGRMETRIC','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$DATAGUARD_CONFIG','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$DATAGUARD_STATS','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$TRANSACTION','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('V_$LOCKED_OBJECT','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('DBA_OBJECTS','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('CDB_DATA_FILES','DATADOG','SELECT',p_grant_option => false);
exec rdsadmin.rdsadmin_util.grant_sys_object('DBA_DATA_FILES','DATADOG','SELECT',p_grant_option => false);
```

<!-- xxz tab xxx -->

<!-- xxx tab "Oracle Autonomous Database" xxx -->
##### Oracle Autonomous Database

###### Create user

Create a read-only login to connect to your server and grant the required permissions:

```SQL
CREATE USER datadog IDENTIFIED BY your_password ;
```

###### Grant permissions 

```SQL
grant create session to datadog ;
grant select on v$session to datadog ;
grant select on v$database to datadog ;
grant select on v$containers to datadog;
grant select on v$sqlstats to datadog ;
grant select on v$instance to datadog ;
grant select on dba_feature_usage_statistics to datadog ;
grant select on V$SQL_PLAN_STATISTICS_ALL to datadog ;
grant select on V$PROCESS to datadog ;
grant select on V$SESSION to datadog ;
grant select on V$CON_SYSMETRIC to datadog ;
grant select on CDB_TABLESPACE_USAGE_METRICS to datadog ;
grant select on CDB_TABLESPACES to datadog ;
grant select on V$SQLCOMMAND to datadog ;
grant select on V$DATAFILE to datadog ;
grant select on V$SYSMETRIC to datadog ;
grant select on V$SGAINFO to datadog ;
grant select on V$PDBS to datadog ;
grant select on CDB_SERVICES to datadog ;
grant select on V$OSSTAT to datadog ;
grant select on V$PARAMETER to datadog ;
grant select on V$SQLSTATS to datadog ;
grant select on V$CONTAINERS to datadog ;
grant select on V$SQL_PLAN_STATISTICS_ALL to datadog ;
grant select on V$SQL to datadog ;
grant select on V$PGASTAT to datadog ;
grant select on v$asm_diskgroup to datadog ;
grant select on v$rsrcmgrmetric to datadog ;
grant select on v$dataguard_config to datadog ;
grant select on v$dataguard_stats to datadog ;
grant select on v$transaction to datadog;
grant select on v$locked_object to datadog;
grant select on dba_objects to datadog;
grant select on cdb_data_files to datadog;
grant select on dba_data_files to datadog;
```

<!-- xxz tab xxx -->

<!-- xxz tabs xxx -->

### Configuration

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

**Note:** For the Agent releases between `7.50.1` (inclusive) and `7.53.0` (exclusive), the configuration subdirectory is `oracle-dbm.d`. For all other Agent releases, the configuration directory is `oracle.d`.

2. [Restart the Agent][7].

#### Connect to Oracle through TCPS

To connect to Oracle through TCPS (TCP with SSL), uncomment the `protocol` configuration option and select `TCPS`. Update the `server` option to set the TCPS server to monitor.

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
        #
        service_name: "<SERVICE_NAME>"
    
        ## @param username - string - required
        ## The username for the user account.
        #
        username: <USER>
    
        ## @param password - string - required
        ## The password for the user account.
        #
        password: "<PASSWORD>"
    
        ## @param protocol - string - optional - default: TCP
        ## The protocol to connect to the Oracle Database Server. Valid protocols include TCP and TCPS.
        ##
        #
        protocol: TCPS
    ```

### Validation

[Run the Agent's status subcommand][9] and look for `oracle` under the Checks section.

### Custom query

Providing custom queries is also supported. Each query must have two parameters:

| Parameter       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |                                                                                                                                                                
| `query`         | This is the SQL to execute. It can be a simple statement or a multi-line script. All rows of the result are evaluated.                                                                                                                                                                                                                                                                                                                        |
| `columns`       | This is a list representing each column, ordered sequentially from left to right. There are two required pieces of data: <br> a. `type` - This is the submission method (`gauge`, `count`, etc.). <br> b. name - This is the suffix used to form the full metric name. If `type` is `tag`, this column is instead considered as a tag which is applied to every metric collected by this particular query. |

Optionally use the `tags` parameter to apply a list of tags to each metric collected.

The following:

```python
self.gauge('oracle.custom_query.metric1', value, tags=['tester:oracle', 'tag1:value'])
self.count('oracle.custom_query.metric2', value, tags=['tester:oracle', 'tag1:value'])
```

is what the following example configuration would become:

```yaml
- query: | # Use the pipe if you require a multi-line script.
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

## Data Collected

### Metrics

See [metadata.csv][11] for a list of metrics provided by this integration.

### Events

The Oracle Database check does not include any events.

### Service Checks

See [service_checks.json][12] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][14].

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/oracle/images/oracle_dashboard.png
[2]: https://docs.datadoghq.com/database_monitoring/
[3]: https://support.microsoft.com/en-us/topic/the-latest-supported-visual-c-downloads-2647da03-1eea-4433-9aff-95f26a218cc0
[4]: https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html#ic_winx64_inst
[5]: https://github.com/DataDog/integrations-core/blob/master/oracle/datadog_checks/oracle/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html
[9]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[10]: https://docs.datadoghq.com/monitors/monitor_types/metric/?tab=threshold
[11]: https://github.com/DataDog/integrations-core/blob/master/oracle/metadata.csv
[12]: https://github.com/DataDog/integrations-core/blob/master/oracle/assets/service_checks.json
[13]: https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html
[14]: https://docs.datadoghq.com/help/
[15]: https://docs.oracle.com/en/database/oracle/oracle-database/19/mxcli/installing-and-removing-oracle-database-client.html

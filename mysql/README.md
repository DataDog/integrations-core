# Overview

The Datadog agent's MySQL check sends many database metrics to Datadog, including metrics for:

* Query throughput
* Query performance (average query run time, slow queries, etc)
* Connections (currently open connections, aborted connections, errors, etc)
* InnoDB (buffer pool metrics, etc)

And [many more](https://github.com/DataDog/integrations-core/blob/master/mysql/metadata.csv). You can also invent your own metrics using custom SQL queries.

The MySQL check sends one service check: whether or not the Datadog agent can connect to MySQL.

It does not send anything to your events stream.

# Installation

The MySQL check is included in the Datadog agent package, so simply [install the Datadog agent](https://app.datadoghq.com/account/settings#agent) on your MySQL servers. If you need the newest version of the MySQL check, install the `dd-check-mysql` package; this package's check will override the one packaged with the agent. See the [integrations-core](https://github.com/DataDog/integrations-core#installing-the-integrations) repository for more details.

# Configuration

### Prepare MySQL

On each MySQL server, create a database user for the Datadog agent:

```
mysql> CREATE USER 'datadog'@'localhost' IDENTIFIED BY '<YOUR_CHOSEN_PASSWORD>';
Query OK, 0 rows affected (0.00 sec)
```

The agent needs a few permissions to collect metrics. Grant its user ONLY the following permissions:

```
mysql> GRANT REPLICATION CLIENT ON *.* TO 'datadog'@'localhost' WITH MAX_USER_CONNECTIONS 5;
Query OK, 0 rows affected, 1 warning (0.00 sec)

mysql> GRANT PROCESS ON *.* TO 'datadog'@'localhost';
Query OK, 0 rows affected (0.00 sec)

mysql> GRANT SELECT ON performance_schema.* TO 'datadog'@'localhost';
Query OK, 0 rows affected (0.00 sec)
```

If your MySQL server doesn't have the `performance_schema` database enabled, do not run the final GRANT. Also do not enable `extra_performance_metrics` in the agent's `mysql.yaml`. (see next subsection)

### Connect the Agent

Create a basic `mysql.yaml` in the agent's `conf.d` directory to connect it to the MySQL server:

```
init_config:

instances:
  - server: localhost
    user: datadog
    pass: <YOUR_CHOSEN_PASSWORD> # from the CREATE USER step earlier
    port: <YOUR_MYSQL_PORT> # e.g. 3306
    options:
        replication: 0
        galera_cluster: 1
        extra_status_metrics: true
        extra_innodb_metrics: true
        extra_performance_metrics: true
        schema_size_metrics: false
        disable_innodb_metrics: false
```

See our [sample mysql.yaml](https://github.com/Datadog/integrations-core/blob/master/mysql/conf.yaml.example) for all available configuration options, including those for custom metrics.

Restart the agent to start sending MySQL metrics to Datadog.

# Validation

Run the agent's `info` subcommand and look for `mysql` under the Checks section:

```
  Checks
  ======

    [...]

    mysql
    -----
      - instance #0 [OK]
      - Collected 168 metrics, 0 events & 1 service check

    [...]
```

If the status is not OK, see the Troubleshooting section.

# Troubleshooting

You may observe one of these common problems in the output of the Datadog agent's `info` subcommand.

### Agent cannot authenticate
```
    mysql
    -----
      - instance #0 [ERROR]: '(1045, u"Access denied for user \'datadog\'@\'localhost\' (using password: YES)")'
      - Collected 0 metrics, 0 events & 1 service check
```

Either the `'datadog'@'localhost'` user doesn't exist or the agent is not configured with correct credentials. Review the Configuration section to add a user, and review the agent's `mysql.yaml`.

### Database user lacks privileges
```
    mysql
    -----
      - instance #0 [WARNING]
          Warning: Privilege error or engine unavailable accessing the INNODB status                          tables (must grant PROCESS): (1227, u'Access denied; you need (at least one of) the PROCESS privilege(s) for this operation')
      - Collected 21 metrics, 0 events & 1 service check
```

The agent can authenticate, but it lacks privileges for one or more metrics it wants to collect. In this case, it lacks the PROCESS privilege:

```
mysql> select user,host,process_priv from mysql.user where user='datadog';
+---------+-----------+--------------+
| user    | host      | process_priv |
+---------+-----------+--------------+
| datadog | localhost | N            |
+---------+-----------+--------------+
1 row in set (0.00 sec)
```

Review the Configuration section and grant the agent's user all necessary permissions. Do NOT grant all privileges on all databases to the agent's user.

# Compatibility

The MySQL integration is supported on versions x.x+

# Agent Check: Snowflake

## Overview

This check monitors [Snowflake][1] through the Datadog Agent. Snowflake is a SaaS-analytic data warehouse and runs completely on cloud infrastructure. 
This integration monitors credit usage, billing, storage, query metrics, and more.

<div class="alert alert-info"><bold>NOTE: Metrics are collected via queries to Snowflake. Queries made by the Datadog integration are billable by Snowflake.</bold></div>

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The Snowflake check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

**Note**: Snowflake check is currently not available for MacOS in Datadog Agent 6 using Python 2.

<div class="alert alert-warning">For users configuring the integration with Agent <code>v7.23.0</code>, upgrade the integration version to <code>2.0.1</code> to take advantage of latest features.
You can upgrade the integration with the following <a href=https://docs.datadoghq.com/agent/guide/integration-management/#install>command</a>:<br>

```text
datadog-agent integration install datadog-snowflake==2.0.1
```
</div>

### Configuration
<div class="alert alert-warning">Snowflake recommends granting permissions to an alternate role like `SYSADMIN`. Read more about controlling <a href="https://docs.snowflake.com/en/user-guide/security-access-control-considerations.html#control-the-assignment-of-the-accountadmin-role-to-users">ACCOUNTADMIN role</a> for more information.</div>

1. Create a Datadog specific role and user to monitor Snowflake. In Snowflake, run the following to create a custom role with access to the ACCOUNT_USAGE schema.

    Note: By default, this integration monitors the `SNOWFLAKE` database and `ACCOUNT_USAGE` schema.
    This database is available by default and only viewable by users in the `ACCOUNTADMIN` role or [any role granted by the ACCOUNTADMIN][8].
    

    ```text
    use role ACCOUNTADMIN;
    grant imported privileges on database snowflake to role SYSADMIN;
    
    use role SYSADMIN;
    
    ```
    
    
    Alternatively, you can create a `DATADOG` custom role with access to `ACCOUNT_USAGE`.
    
    
    ```text
    -- Create a new role intended to monitor Snowflake usage.
    create role DATADOG;
   
    -- Grant privileges on the SNOWFLAKE database to the new role.
    grant imported privileges on database SNOWFLAKE to role DATADOG;

    -- Create a user, skip this step if you are using an existing user.
    create user DATADOG_USER
    LOGIN_NAME = DATADOG_USER
    password = '<PASSWORD>'
    default_warehouse = <WAREHOUSE>
    default_role = DATADOG
    default_namespace = SNOWFLAKE.ACCOUNT_USAGE;
   
    -- Grant the monitor role to the user.
    grant role DATADOG to user <USER>;
    ```
   

2. Edit the `snowflake.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Snowflake performance data. See the [sample snowflake.d/conf.yaml][3] for all available configuration options.

    ```yaml
        ## @param account - string - required
        ## Name of your account (provided by Snowflake), including the platform and region if applicable.
        ## For more information on Snowflake account names,
        ## see https://docs.snowflake.com/en/user-guide/connecting.html#your-snowflake-account-name
        #
      - account: <ACCOUNT>
    
        ## @param user - string - required
        ## Login name for the user.
        #
        user: <USER>
    
        ## @param password - string - required
        ## Password for the user
        #
        password: <PASSWORD>
   
        ## @param role - string - required
        ## Name of the role to use.
        ##
        ## By default, the SNOWFLAKE database is only accessible by the ACCOUNTADMIN role. Snowflake recommends
        ## configuring a role specific for monitoring:
        ## https://docs.snowflake.com/en/sql-reference/account-usage.html#enabling-account-usage-for-other-roles
        #
        role: <ROLE>
   
        ## @param min_collection_interval - number - optional - default: 3600
        ## This changes the collection interval of the check. For more information, see:
        ## https://docs.datadoghq.com/developers/write_agent_check/#collection-interval
        ##
        ## NOTE: Most Snowflake ACCOUNT_USAGE views are populated on an hourly basis,
        ## so to minimize unnecessary queries the `min_collection_interval` defaults to 1 hour.
        #
        min_collection_interval: 3600
    ```

    <div class="alert alert-info">By default, the <code>min_collection_interval</code> is 1 hour. 
    Snowflake metrics are aggregated by day, you can increase the interval to reduce the number of queries.<br>
    <bold>Note</bold>: Snowflake ACCOUNT_USAGE views have a <a href="https://docs.snowflake.com/en/sql-reference/account-usage.html#data-latency">known latency</a> of 45 minutes to 3 hours.</div>

3. [Restart the Agent][4].

#### Proxy configuration

Snowflake recommends setting [environment variables for proxy configuration][12].

You can also set the `proxy_host`, `proxy_port`, `proxy_user`, and `proxy_password` under `init_config` in the [snowflake.d/conf.yaml][3].

**NOTE**: Snowflake automatically formats the proxy configurations and sets [standard proxy environment variables][13]. 
These variables also impact every requests from integrations, including orchestrators like Docker, ECS, and Kubernetes.

### Snowflake Custom Queries

The Snowflake integration supports custom queries. By default, the integration connects to the shared `SNOWFLAKE` database and `ACCOUNT_USAGE` schema. 

If you want to run custom queries in a different schema or database, add another instance to the [sample snowflake.d/conf.yaml][3] and specify the `database` and `schema` options.
Ensure the user and role has access to the specified database or schema.

#### Configuration options
The `custom_queries` option has the following options:

| Option        | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|---------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| query         | Yes      | This is the SQL to execute. It can be a simple statement or a multi-line script. All of the rows of the results are evaluated. Use the pipe if you require a multi-line script.                                                                                                                                                                                                                                                                                                                                                                                                                              |
| columns       | Yes      | This is a list representing each column ordered sequentially from left to right.<br><br>There are 2 required pieces of data:<br>  - **`name`**: This is the suffix to append to the metric_prefix to form the full metric name. If the `type` is specified as `tag`, the column is instead applied as a tag to every metric collected by this query.<br>  - **`type`**: This is the submission method (`gauge`, `count`, `rate`, etc.). This can also be set to `tag` to tag each metric in the row with the name and value (`<name>:<row_value>`) of the item in this column. |
| tags          | No       | A list of static tags to apply to each metric.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |


##### Notes
- At least one item in defined `columns` should be a metric type (`gauge`, `count`, `rate`, etc).
- The number of items in columns must equal the number of columns returned in the query.
- The order in which the items in `columns` are defined must be in the same order returned in the query

```yaml
custom_queries:
  - query: select F3, F2, F1 from Table;
    columns:
      - name: f3_metric_alias
        type: gauge
      - name: f2_tagkey
        type: tag
      - name: f1_metric_alias
        type: count
    tags:
      - test:snowflake
```

#### Example
The following example is a query that will count all queries in the [`QUERY_HISTORY` view][9] tagged by database, schema, and warehouse names.

```TEXT
select count(*), DATABASE_NAME, SCHEMA_NAME, WAREHOUSE_NAME from QUERY_HISTORY group by 2, 3, 4;
```

##### Configuration

The custom query configuration in `instances` will look like the following:

```yaml
custom_queries:
  - query: select count(*), DATABASE_NAME, SCHEMA_NAME, WAREHOUSE_NAME from QUERY_HISTORY group by 2, 3, 4;
    columns:
      - name: query.total
        type: gauge
      - name: database_name
        type: tag
      - name: schema_name
        type: tag
      - name: warehouse_name
        type: tag
    tags:
      - test:snowflake
```

##### Validation

To verify the result, search for the metrics using [Metrics Summary][11]:

![Snowflake Metric Summary][10]


### Validation

[Run the Agent's status subcommand][5] and look for `snowflake` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this check.

### Service Checks

**snowflake.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot authenticate and connect to Snowflake, `OK` otherwise.

### Events

Snowflake does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://www.snowflake.com/
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://github.com/DataDog/integrations-core/blob/master/snowflake/datadog_checks/snowflake/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[6]: https://github.com/DataDog/integrations-core/blob/master/snowflake/metadata.csv
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.snowflake.com/en/sql-reference/account-usage.html#enabling-account-usage-for-other-roles
[9]: https://docs.snowflake.com/en/sql-reference/account-usage/query_history.html
[10]: https://raw.githubusercontent.com/DataDog/integrations-core/master/snowflake/images/custom_query.png
[11]: https://docs.datadoghq.com/metrics/summary/
[12]: https://docs.snowflake.com/en/user-guide/python-connector-example.html#using-a-proxy-server
[13]: https://github.com/snowflakedb/snowflake-connector-python/blob/d6df58f1c338b255393571a08a1f9f3a71d8f7b6/src/snowflake/connector/proxy.py#L40-L41

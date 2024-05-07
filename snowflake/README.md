# Agent Check: Snowflake

## Overview

This check monitors [Snowflake][1] through the Datadog Agent. Snowflake is a SaaS-analytic data warehouse and runs completely on cloud infrastructure. 
This integration monitors credit usage, billing, storage, query metrics, and more.

<div class="alert alert-info"><bold>Note</bold>: Metrics are collected with queries to Snowflake. Queries made by the Datadog integration are billable by Snowflake.</div>

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host.

### Installation

The Snowflake check is included in the [Datadog Agent][2] package.

**Note**: The Snowflake check is not available in Datadog Agent v6 using Python 2. To use Snowflake on Agent v6 see [Use Python 3 with Datadog Agent v6][3] or upgrade to Agent v7.

### Configuration
<div class="alert alert-warning">Snowflake recommends granting permissions to an alternate role like `SYSADMIN`. Read more about controlling <a href="https://docs.snowflake.com/en/user-guide/security-access-control-considerations.html#control-the-assignment-of-the-accountadmin-role-to-users">ACCOUNTADMIN role</a> for more information.</div>

1. Create a Datadog specific role and user to monitor Snowflake. In Snowflake, run the following to create a custom role with access to the ACCOUNT_USAGE schema.

    Note: By default, this integration monitors the `SNOWFLAKE` database and `ACCOUNT_USAGE` schema. See "Collecting Organization Data" for information on how to monitor the `ORGANIZATION_USAGE` schema.
    This database is available by default and only viewable by users in the `ACCOUNTADMIN` role or [any role granted by the ACCOUNTADMIN][4].
    

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

    -- Grant usage to your default warehouse to the role DATADOG.
   grant usage on warehouse <WAREHOUSE> to role DATADOG;

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
   

2. Edit the `snowflake.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Snowflake performance data. See the [sample snowflake.d/conf.yaml][5] for all available configuration options.

    ```yaml
        ## @param account - string - required
        ## Name of your account (provided by Snowflake), including the platform and region if applicable.
        ## For more information on Snowflake account names,
        ## see https://docs.snowflake.com/en/user-guide/connecting.html#your-snowflake-account-name
        #
      - account: <ORG_NAME>-<ACCOUNT_NAME>
    
        ## @param username - string - required
        ## Login name for the user.
        #
        username: <USER>
    
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
   
        ## @param min_collection_interval - number - optional - default: 15
        ## This changes the collection interval of the check. For more information, see:
        ## https://docs.datadoghq.com/developers/write_agent_check/#collection-interval
        ##
        ## NOTE: Most Snowflake ACCOUNT_USAGE views are populated on an hourly basis,
        ## so to minimize unnecessary queries, set the `min_collection_interval` to 1 hour.
        #
        min_collection_interval: 3600
   
        # @param disable_generic_tags - boolean - optional - default: false
        # Generic tags such as `cluster` will be replaced by <integration_name>_cluster to avoid
        # getting mixed with other integration tags.
        # disable_generic_tags: true
    ```

    <div class="alert alert-info">In the default `conf.yaml`, the <code>min_collection_interval</code> is 1 hour. 
    Snowflake metrics are aggregated by day, you can increase the interval to reduce the number of queries.<br>
    <bold>Note</bold>: Snowflake ACCOUNT_USAGE views have a <a href="https://docs.snowflake.com/en/sql-reference/account-usage.html#data-latency">known latency</a> of 45 minutes to 3 hours.</div>

3. [Restart the Agent][6].

#### Collecting Organization Data

By default, this integration monitors the `ACCOUNT_USAGE` schema, but it can be set to monitor organization-level metrics instead.

To collect organization metrics, change the schema field to `ORGANIZATION_USAGE` and increase the `min_collection_interval` to 43200 in the integration's configuration. This reduces the number of queries to Snowflake, as most organization queries have a latency of up to 24 hours.

Note: To monitor organization metrics, your `user` must have the `ORGADMIN` role.

  ```yaml
      - schema: ORGANIZATION_USAGE
        min_collection_interval: 43200
  ```

Only some organization metrics are enabled by default. To collect all available organization metrics, utilize the `metric_groups` configuration option:

  ```yaml
      metric_groups:
        - snowflake.organization.warehouse
        - snowflake.organization.currency
        - snowflake.organization.credit
        - snowflake.organization.storage
        - snowflake.organization.contracts
        - snowflake.organization.balance
        - snowflake.organization.rate
        - snowflake.organization.data_transfer
  ```

Additionally, you can monitor both account and organization metrics at the same time:

  ```yaml
      instances:
      - account: example-inc
        username: DATADOG_ORG_ADMIN
        password: '<PASSWORD>'
        role: SYSADMIN
        schema: ORGANIZATION_USAGE
        database: SNOWFLAKE
        min_collection_interval: 43200

      - account: example-inc
        username: DATADOG_ACCOUNT_ADMIN
        password: '<PASSWORD>'
        role: DATADOG_ADMIN
        schema: ACCOUNT_USAGE
        database: SNOWFLAKE
        min_collection_interval: 3600
  ```

#### Collecting data for multiple environments

If you want to collect data for multiple Snowflake environments, add each environment as an instance in your `snowflake.d/conf.yaml` file. For example, if you needed to collect data for two users named `DATADOG_SYSADMIN` and `DATADOG_USER`:

```yaml
instances:
  - account: example-inc
    username: DATADOG_SYSADMIN
    password: '<PASSWORD>'
    role: SYSADMIN
    database: EXAMPLE-INC

  - account: example-inc
    username: DATADOG_USER
    password: '<PASSWORD>'
    role: DATADOG_USER
    database: EXAMPLE-INC
```

#### Proxy configuration

Snowflake recommends setting [environment variables for proxy configuration][7].

You can also set the `proxy_host`, `proxy_port`, `proxy_user`, and `proxy_password` under `init_config` in the [snowflake.d/conf.yaml][5].

**NOTE**: Snowflake automatically formats the proxy configurations and sets [standard proxy environment variables][8]. 
These variables also impact every requests from integrations, including orchestrators like Docker, ECS, and Kubernetes.

#### Private connectivity to Snowflake configuration

If [private connectivity][9] (such as [AWS PrivateLink][10]) is enabled in Snowflake, you can configure the Snowflake integration by updating the `account` configuration option to the following format:

  ```yaml
        - account: <ACCOUNT>.<REGION_ID>.privatelink
  ```

### Snowflake custom queries

The Snowflake integration supports custom queries. By default, the integration connects to the shared `SNOWFLAKE` database and `ACCOUNT_USAGE` schema. 

To run custom queries in a different schema or database, add another instance to the [sample snowflake.d/conf.yaml][5] and specify the `database` and `schema` options.
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
The following example is a query that counts all queries in the [`QUERY_HISTORY` view][11] tagged by database, schema, and warehouse names.

```TEXT
select count(*), DATABASE_NAME, SCHEMA_NAME, WAREHOUSE_NAME from QUERY_HISTORY group by 2, 3, 4;
```

##### Configuration

The custom query configuration in `instances` looks like the following:

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

To verify the result, search for the metrics using [Metrics Summary][12]:

![Snowflake Metric Summary][13]


### Validation

[Run the Agent's status subcommand][14] and look for `snowflake` under the Checks section.

## Data Collected

<div class="alert alert-info"><bold>Note</bold>: Only metrics from the following metric groups are enabled by default: <code>snowflake.query.*</code>, <code>snowflake.billing.*</code>, <code>snowflake.storage.*</code>, and <code>snowflake.logins.*</code>.

If you would like to collect metrics from other metric groups, please refer <a href="https://github.com/DataDog/integrations-core/blob/master/snowflake/datadog_checks/snowflake/data/conf.yaml.example">to the example config file for this integration</a>.
</div>

### Metrics

See [metadata.csv][15] for a list of metrics provided by this check.

### Events

Snowflake does not include any events.

### Service Checks

See [service_checks.json][16] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][17].

## Further Reading

Additional helpful documentation, links, and articles:

- [Monitor Snowflake with Datadog][18]


[1]: https://www.snowflake.com/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-v6-python-3/?tab=hostagent
[4]: https://docs.snowflake.com/en/sql-reference/account-usage.html#enabling-account-usage-for-other-roles
[5]: https://github.com/DataDog/integrations-core/blob/master/snowflake/datadog_checks/snowflake/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.snowflake.com/en/user-guide/python-connector-example.html#using-a-proxy-server
[8]: https://github.com/snowflakedb/snowflake-connector-python/blob/d6df58f1c338b255393571a08a1f9f3a71d8f7b6/src/snowflake/connector/proxy.py#L40-L41
[9]: https://docs.snowflake.com/en/user-guide/private-snowflake-service.html
[10]: https://docs.snowflake.com/en/user-guide/admin-security-privatelink.html
[11]: https://docs.snowflake.com/en/sql-reference/account-usage/query_history.html
[12]: https://docs.datadoghq.com/metrics/summary/
[13]: https://raw.githubusercontent.com/DataDog/integrations-core/master/snowflake/images/custom_query.png
[14]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[15]: https://github.com/DataDog/integrations-core/blob/master/snowflake/metadata.csv
[16]: https://github.com/DataDog/integrations-core/blob/master/snowflake/assets/service_checks.json
[17]: https://docs.datadoghq.com/help/
[18]: https://www.datadoghq.com/blog/snowflake-monitoring-datadog/

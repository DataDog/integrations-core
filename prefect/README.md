# Agent Check: Prefect

## Overview

This check monitors [Prefect server][1] through the Datadog Agent.

Prefect is a Python-first workflow orchestration platform used to schedule and execute flows and tasks across work pools, work queues, and workers. This integration collects orchestration health and performance metrics and events directly from the [Prefect server API][2] and supports [log collection][3] for comprehensive monitoring.

### What this integration monitors

The integration collects metrics across multiple layers of the Prefect orchestration hierarchy:

-   **Server health**: API readiness and health status to confirm the control plane is operational.
-   **Work pool layer**: Pool readiness, paused or not-ready state, and aggregated worker availability to detect capacity or configuration issues.
-   **Worker layer**: Online or offline status and heartbeat age to identify lost or unhealthy workers.
-   **Work queue layer**: Backlog size, backlog age, last polled age, concurrency utilization, and queue state (ready, paused or not-ready) to detect congestion, starvation, and stalled consumers.
-   **Concurrency limit layer**: Configured limit and occupied slots for global and task run (tag-based) concurrency limits to detect saturation.
-   **Deployment and flow layer**: Flow run counts by state (running, completed, failed, crashed, etc.), throughput, late starts, execution duration, queue wait time, and retry gaps to track reliability and latency percentiles.
-   **Task layer**: Task run counts by state, throughput, execution duration, and dependency wait time to enable drilldowns from slow flows to individual task bottlenecks.
-   **Events**: Prefect events for state transitions and lifecycle changes.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][4] for guidance on applying these instructions.

### Installation

The Prefect check is included in the [Datadog Agent][5] package.
No additional installation is needed on your server.

### Configuration

1. Edit the `prefect.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Prefect performance data. See the [sample prefect.d/conf.yaml][6] for all available configuration options.

2. [Restart the Agent][7].

#### Authentication

For a self-hosted server using `PREFECT_SERVER_API_AUTH_STRING`, set the
`prefect_userpass` option to the same `user:password` secret used by Prefect clients
in `PREFECT_API_AUTH_STRING`. The integration does not read Prefect environment
variables automatically. For example, reference a secret resolved by the
[Agent secret management mechanism][14]:

```yaml
instances:
  - prefect_url: https://prefect.example/api
    prefect_userpass: ENC[prefect_api_auth_string]
```

Passwords may contain colons. Alternatively, keep using the existing separate
`username` and `password` options. Do not combine them with `prefect_userpass`, and
use `prefect_userpass` only with basic authentication. Use HTTPS when sending credentials
to a remote server.

### Configure the Related Databases dashboard section

The Related Databases section of the Prefect dashboard shows the PostgreSQL database and Redis instance that Prefect server uses. This section requires the Datadog [PostgreSQL][11] and [Redis][12] integrations to monitor those instances. Set the same `service` on the Prefect, PostgreSQL, and Redis instances, then select that value in the `service` template variable to filter the whole dashboard.

The PostgreSQL widgets stay empty if Prefect server uses its default SQLite database. They show data only when `PREFECT_SERVER_DATABASE_CONNECTION_URL` points to a PostgreSQL database. The Redis widgets stay empty unless Prefect server uses the `prefect-redis` package for event messaging, with `PREFECT_MESSAGING_BROKER` and `PREFECT_MESSAGING_CACHE` set to `prefect_redis.messaging`. For more information, see [Scale self-hosted Prefect][13].

1. Set `service` on the instance in your `prefect.d/conf.yaml` file:

    ```yaml
    instances:
      - prefect_url: http://localhost:4200/api
        service: prefect
    ```

2. In your `postgres.d/conf.yaml` file, add an instance for the Prefect database. Set `dbname` to the database name in `PREFECT_SERVER_DATABASE_CONNECTION_URL`, and set `dbstrict` to `true`. If another instance already monitors the server, add this one as a separate instance.

    **Note**: Without `dbstrict`, the check collects per-database metrics for every database on the server. If the server is shared, the dashboard includes other applications' databases.

    ```yaml
    instances:
      - host: <POSTGRES_HOST>
        port: 5432
        username: datadog
        password: <PASSWORD>
        dbname: prefect
        dbstrict: true
        service: prefect
    ```

3. Set `service` on the instance in your `redisdb.d/conf.yaml` file:

    ```yaml
    instances:
      - host: <REDIS_HOST>
        port: 6379
        service: prefect
    ```

4. [Restart the Agent][7].

### Validation

[Run the Agent's status subcommand][8] and look for `prefect` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this integration.

### Logs 
1. Enable log collection in your `datadog.yaml` file:

    ```
    logs_enabled: true
    ```
2. Uncomment and edit the logs configuration block in your `prefect.d/conf.yaml` file. For example:

    ```
    logs:
      - type: docker
        source: prefect
        service: <SERVICE>
    ```

### Events

The Prefect integration includes event support. Events are disabled by default; to enable them, set `collect_events` to `true` in the configuration.

After you enable it, the integration submits flow-run, task-run, and ready or not-ready events. The set of submitted events can be customized by adding or removing entries in the configuration.

### Service Checks

The Prefect integration does not include any service checks.


## Uninstallation

To disable the integration, rename the configuration file from `prefect.d/conf.yaml` to `prefect.d/conf.yaml.example`. Alternatively, if you are running a containerized environment, you can remove the annotation used to enable the integration.

## Support

Need help? Contact [Datadog support][10].

[1]: https://www.prefect.io/
[2]: https://docs.prefect.io/v3/api-ref/rest-api/server/index
[3]: https://docs.datadoghq.com/logs/log_collection/
[4]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[5]: https://app.datadoghq.com/account/settings/agent/latest
[6]: https://github.com/DataDog/integrations-core/blob/master/prefect/datadog_checks/prefect/data/conf.yaml.example
[7]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[8]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/prefect/metadata.csv
[10]: https://docs.datadoghq.com/help/
[11]: https://docs.datadoghq.com/integrations/postgres/
[12]: https://docs.datadoghq.com/integrations/redis/
[13]: https://docs.prefect.io/v3/advanced/self-hosted
[14]: https://docs.datadoghq.com/agent/configuration/secrets-management/

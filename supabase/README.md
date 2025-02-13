# Agent Check: Supabase

## Overview

This check monitors [Supabase][1] through the Datadog Agent. 

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

Starting from Agent release 7.62.0, the Supabase check is included in the Datadog Agent package. No additional installation is needed in your environment.

This check uses OpenMetrics to collect metrics from the OpenMetrics endpoint that Supabase exposes, which requires Python 3.

### Configuration

Supabase platform comes with a Prometheus-compatible metrics endpoint readily accessible at your project's `metrics` endpoint: `https://<project-ref>.supabase.co/customer/v1/privileged/metrics`. Access to the endpoint is secured via HTTP Basic Auth; the `username` is `service_role`, while the `password` is the service role JWT available through the Supabase dashboard.

```yaml
## All options defined here are available to all instances.
#
init_config:

instances:

    # The endpoint exposing Supabase customer metrics
    #
  - privileged_metrics_endpoint:  https://<project-ref>.supabase.co/customer/v1/privileged/metrics

    ## @param username - string - optional
    ## The username to use if services are behind basic or digest auth.
    #
    username: service_role

    ## @param password - string - optional
    ## The password to use if services are behind basic or NTLM auth.
    #
    password: <JWT>
```

It also comes with a hosted Postgres database. To integrate with the Agent, you need to [prepare Postgres][10] then supply the database configuration to the integration configuration. 
```yaml
## All options defined here are available to all instances.
#
init_config:

instances:

    ## @param host - string - required
    ## The hostname to connect to.
    #
  - host: <HOST>

    ## @param port - integer - optional - default: 5432
    ## The port to use when connecting to PostgreSQL.
    #
    port: 6543

    ## @param username - string - required
    ## The Datadog username created to connect to PostgreSQL.
    #
    username: datadog.<PROJECT-REF>

    ## @param password - string - optional
    ## The password associated with the Datadog user.
    #
    password: <UNIQUEPASSWORD>
    
    ## @param dbname - string - optional - default: postgres
    ## The name of the PostgreSQL database to monitor.
    ## Note: If omitted, the default system Postgres database is queried.
    #
    dbname: <DATABASE>
```

[Supabase Storage][11] comes with a Prometheus-compatible metrics endpoint readily accessible at `/metrics` on port `5000`. For the Agent to start collecting metrics, the Supabase Storage container needs to be annotated. For more information about annotations, refer to the [Autodiscovery Integration Templates][3] for guidance. You can find additional configuration options by reviewing the [sample supabase.d/conf.yaml][4].

Note: Integration with Supabase Storage is only available in the self-hosted architecture. `storage_api_endpoint` should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `5000`. In containerized environments, `%%host%%` should be used for [host autodetection][3].

### Validation

[Run the Agent's status subcommand][6] and look for `supabase` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Supabase integration does not include any events.

### Service Checks

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://supabase.com/docs
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/supabase/datadog_checks/supabase/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/supabase/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/supabase/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/integrations/postgres/?tab=host#prepare-postgres
[11]: https://github.com/supabase/storage/tree/master

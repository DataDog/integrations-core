# Agent Check: Fly.io

<div class="alert alert-warning">
This integration is in public beta. Use caution if enabling it on production workloads.
</div>

## Overview

This check monitors [Fly.io][1] metrics through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a Fly application.

### Installation

The Fly.io check is included in the [Datadog Agent][2] package. We recommend running the Fly.io check on the Datadog Agent in a Fly.io application. The Agent collects [Prometheus metrics][19] as well as some additional data from the [Machines API][20]. Additionally, you can configure the Agent to receive [traces](#Application-Traces) and custom metrics from all of your Fly.io applications inside the organization.

#### Deploying the Agent as a Fly.io application

1. Create a new application in Fly.io with the image set as the [Datadog Agent][15] when launching, or provide the image in the `fly.toml` file:

    ```
    [build]
        image = 'gcr.io/datadoghq/agent:7'
    ```

2. Set a [secret][17] for your Datadog API key called `DD_API_KEY`, and optionally your [site][14] as `DD_SITE`.

3. In your app's directory, create a `conf.yaml` file for the Fly.io integration, [configure](#Configuration) the integration, and mount it in the Agent's `conf.d/fly_io.d/` directory as `conf.yaml`:

    ```
    instances:
    - empty_default_hostname: true
      headers:
          Authorization: Bearer <YOUR_FLY_TOKEN>
      machines_api_endpoint: http://_api.internal:4280
      org_slug: <YOUR_ORG_SLUG>
    ```

4. [Deploy][16] your app.

**Note**: To collect traces and custom metrics from your applications, see [Application traces](#Application-traces).

### Configuration

1. Edit the `fly_io.d/conf.yaml` file, located in the `conf.d/` folder at the root of your Agent's configuration directory, to start collecting your Fly.io performance data. See the [sample fly_io.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `fly_io` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Fly.io integration does not include any events.

### Service Checks

The Fly.io integration does not include any service checks.

### Application traces

Follow these steps to collect traces for an application in your Fly.io environment.

1. [Instrument][12] your application.
2. [Deploy](#deploying-the-agent-as-a-flyio-application) the Datadog Agent as a Fly.io application.
3. Set the required environment variables in the `fly.toml` or `Dockerfile` of your application and deploy the app.

    Set the following as an environment variable to submit metrics to the Datadog Agent application:
    ```
    [env]
        DD_AGENT_HOST="<YOUR_AGENT_APP_NAME>.internal"

    ```

    Set the following environment variable to ensure you report the same host for logs and metrics:
    ```
    DD_TRACE_REPORT_HOSTNAME="true"
    ```

    To utilize [unified service tagging][13], set these environment variables:
    ```
    DD_SERVICE="APP_NAME"
    DD_ENV="ENV_NAME"
    DD_VERSION="VERSION"
    ```

    To correlate logs and traces, follow these [steps][11] and set this environment variable:
    ```
    DD_LOGS_INJECTION="true"
    ```

4. Set the following environment variables in your [Datadog Agent application's](#Deploying-the-agent-as-a-Fly.io-application) `fly.toml` and deploy the app:

    ```
    [env]
        DD_APM_ENABLED = "true"
        DD_APM_NON_LOCAL_TRAFFIC = "true"
        DD_DOGSTATSD_NON_LOCAL_TRAFFIC = "true"
        DD_BIND_HOST = "fly-global-services"
    ```

**Note**: Ensure that the settings on your Fly.io instances do not publicly expose the ports for APM and DogStatsD, if enabled.

### Log collection

Use the [fly_logs_shipper][10] to collect logs from your Fly.io applications.

1. Clone the logs shipper [project][10].

2. Modify the `vector-configs/vector.toml` file to set the logs source as `fly_io`:

    ```
    [transforms.log_json]
    type = "remap"
    inputs = ["nats"]
    source  = '''
    . = parse_json!(.message)
    .ddsource = 'fly-io'
    .host = .fly.app.instance
    .env = <YOUR_ENV_NAME>
    '''
    ```

This configuration will parse basic fly-specific log attributes. To fully parse all log attributes, set `ddsource` to a [known logs integration][21] on a per-app basis using [vector transforms][22].

3. Set [secrets][17] for [NATS][18]:
`ORG` and `ACCESS_TOKEN`

4. Set [secrets][17] for [Datadog][3]: `DATADOG_API_KEY` and `DATADOG_SITE`

5. [Deploy][6] the logs shipper app.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://fly.io/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/superfly/fly-log-shipper?tab=readme-ov-file#datadog
[4]: https://github.com/DataDog/integrations-core/blob/master/fly_io/datadog_checks/fly_io/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/fly_io/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/fly_io/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://github.com/superfly/fly-log-shipper
[11]: https://docs.datadoghq.com/tracing/other_telemetry/connect_logs_and_traces/
[12]: https://docs.datadoghq.com/tracing/trace_collection/#instrumentation-types
[13]: https://docs.datadoghq.com/getting_started/tagging/unified_service_tagging/?tab=docker#configuration-1
[14]: https://docs.datadoghq.com/agent/troubleshooting/site/
[15]: https://console.cloud.google.com/artifacts/docker/datadoghq/us/gcr.io/agent
[16]: https://fly.io/docs/flyctl/deploy/
[17]: https://fly.io/docs/flyctl/secrets/
[18]: https://github.com/superfly/fly-log-shipper?tab=readme-ov-file#nats-source-configuration
[19]: https://fly.io/docs/metrics-and-logs/metrics/#prometheus-on-fly-io
[20]: https://fly.io/docs/machines/api/
[21]: https://docs.datadoghq.com/logs/log_configuration/pipelines/?tab=source#integration-pipeline-library
[22]: https://vector.dev/docs/reference/configuration/transforms/lua/
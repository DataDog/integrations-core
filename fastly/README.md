{{< img src="integrations/fastly/fastlygraph.png" alt="Fastly Graph" popup="true">}}

## Overview

Connect to Fastly to see key Fastly metrics (like cache coverage and header size) in context with the rest of your Datadog metrics.

## Setup

### Installation

No installation steps required.

### Configuration

#### Metric collection

Create a Read-only access API token on Fastly's token management page, get your Service ID from the Dashboard and enter them in the [Fastly integration tile][1].

<div class="alert alert-info">
The ServiceID is the alphanumerical code, for example: <code>5VqE6MOOy1QFJbgmCK41pY</code> (example from the <a href="https://docs.fastly.com/api/auth">Fastly API documentation</a>).
</div>

If you are using multiple Service IDs from one account, enter an API token on each line.

#### Log collection

{{< site-region region="us3" >}}

Log collection is not supported for this site.

{{< /site-region >}}

{{< site-region region="us,eu,gov" >}}

Configure the Datadog endpoint to forward Fastly logs to Datadog. You can choose the `Datadog` or `Datadog (via Syslog)` endpoint. The `Datadog` endpoint is recommended for more reliable delivery of logs over Syslog.

##### Select the logging endpoint

1. Log in to the Fastly web interface and click **Configure link**.
2. From the **Service** menu, select the appropriate service.
3. Click the **Configuration** button and then select **Clone active**. The Domains page appears.
4. Click the **Logging** link. The logging endpoints page appears. Click **Create Endpoint** under **Datadog** or the **Datadog (with Syslog)** options.

##### Configure the Datadog endpoint (recommended)

1. Give a name to the endpoint, for example: `Datadog`.
2. Configure the log format. By default, the recommended [Datadog-Fastly log format][2] is already provided and can be customized.
3. Select your region to match your Datadog account region: {{< region-param key="dd_site_name" code="true" >}}
4. Add your [Datadog API key][3].
5. Click **Create** at the bottom.
6. Click **Activate** at the top right to activate the new configuration. After a few minutes, logs should begin flowing into your account.

##### Configure the Syslog endpoint

1. Give a name to the endpoint, for example: `Datadog`.
2. Configure the log format to include the recommended [Datadog-Fastly log format][2] with [your Datadog API key][3] at the beginning.

    ```text
    <DATADOG_API_KEY> <DATADOG_FASTLY_LOG_FORMAT>
    ```

    **Note**: Your Datadog API key MUST be in front of the Datadog-Fastly log format for your logs to display in Datadog. See [Useful variables to log][4] for more details.

3. Set **Syslog Address** to: {{< region-param key="web_integrations_endpoint" code="true" >}}
4. Set **Port** to: {{< region-param key="web_integrations_port" code="true" >}}
5. Set **TLS** to `yes`
6. Set **TLS Hostname** to: {{< region-param key="web_integrations_endpoint" code="true" >}}
7. In the advanced option section, select `Blank` as **log line format**
8. Finally, save the endpoint and deploy the service. See the logs in your [Datadog Logs Explorer][5].

[2]: https://docs.datadoghq.com/resources/json/fastly_format.json
[3]: https://app.datadoghq.com/organization-settings/api-keys
[4]: https://docs.fastly.com/guides/streaming-logs/useful-variables-to-log
[5]: https://app.datadoghq.com/logs

{{< /site-region >}}

## Data Collected

### Metrics

See [metadata.csv][6] for a list of metrics provided by this integration.

### Events

The Fastly integration does not include any events.

### Service Checks

The Fastly integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][7].

[1]: https://app.datadoghq.com/account/settings#integrations/fastly
[6]: https://github.com/DataDog/dogweb/blob/prod/integration/fastly/fastly_metadata.csv
[7]: https://docs.datadoghq.com/help/

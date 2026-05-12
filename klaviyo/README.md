# Klaviyo

## Overview

[Klaviyo][1] is a cloud-based email and SMS marketing automation platform supporting integrations with major eCommerce, ads, and CRM platforms.

Integrate Klaviyo with Datadog to gain insights into marketing campaign communication and track eCommerce performance based on Klaviyo events.

## Setup

The user who authenticates this integration must have access to the following Klaviyo Scopes:

- `accounts:read`
- `events:read`
- `flows:read`
- `metrics:read`

To add a new Klaviyo account, click the **Authorize** button and follow the instructions. Once you are redirected back to this page and the authentication is successful, your logs should be available within 5 minutes.

You can view your logs in the [Log Explorer][2]. Ensure you have a [Logs Index][3] set up for `source:klaviyo`.

## Data Collected

### Logs
The Klaviyo integration forwards the marketing and eCommerce events as logs to Datadog.

### Metrics

Klaviyo does not include any metrics.

### Service Checks

Klaviyo does not include any service checks.

### Events

Klaviyo does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][4].

[1]: https://www.klaviyo.com/
[2]: /logs?query=source%3Aklaviyo%2A
[3]: /logs/pipelines/indexes
[4]: https://docs.datadoghq.com/help/


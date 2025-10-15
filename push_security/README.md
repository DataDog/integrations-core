# Push Security

## Overview

[Push Security][1] is an identity security platform that focuses on securing workforce identities through browser-level monitoring. It uses a browser extension to provide real-time visibility into user activity, enabling the detection and response to threats such as phishing, session hijacking, and credential misuse.

Integrate Push Security with Datadog's pre-built dashboard visualizations to gain insights into [Events][2]. With Datadog's built-in log pipelines, you can parse and enrich these logs to facilitate easy search and detailed insights. Additionally, this integration includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Configuration

#### Webhook Configuration

Configure the Datadog endpoint to forward Push Security events as logs to Datadog:

1. Copy the generated URL inside the **Configuration** tab on the Datadog [Push Security][5] tile.
2. Sign in to [Push Security Portal][3].
3. Go to **Settings** > **Webhooks**.
4. Click **+ Webhook**.
5. In the URL field, enter the webhook URL generated in step 1.
6. Under the **Select Events** section, make sure the following checkboxes are selected:
    - Activity
    - Audit
    - Controls
    - Detections
    - Entities
7. Click **Generate Webhook**.

## Data Collected

### Logs

The Push Security integration collects activity, audit, control, detection and entity events.

### Metrics

The Push Security integration does not include any metrics.

### Events

The Push Security integration does not include any events.

## Support

For further assistance, contact [Datadog support][4].

[1]: https://pushsecurity.com/
[2]: https://pushsecurity.redoc.ly/webhooks-v1#operation/account-event
[3]: http://login.pushsecurity.com/u/login
[4]: https://docs.datadoghq.com/help/
[5]: /integrations/push-security
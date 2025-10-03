## Overview

[Proofpoint TAP (Targeted Attack Protection)][1] is a cybersecurity solution designed to detect, mitigate, and block advanced threats that target people through email. It uses a next-generation email security platform to provide visibility into all email communications.

This integration ingests the following logs:

- **Click Events**: These logs provide information about user interactions with links in emails, including whether clicks were permitted or blocked, along with associated threat identification.
- **Message Events**: These logs provide information about email messages analyzed by Proofpoint TAP, including detection outcomes, delivery status (such as delivered or blocked), and threat identification.

This integration gathers and forwards above mentioned events to Datadog for seamless analysis. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. With preconfigured dashboards, the integration offers clear visibility into activities within the Proofpoint TAP platform. Additionally, it includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

**Minimum Agent version:** 7.67.1

## Setup

### Generate Service Credentials in Proofpoint TAP

1. Login to the **Proofpoint TAP** dashboard.
2. Navigate to **Settings > Connected Applications**.
3. Click **Create New Credential**.
4. Name the **new credential set** and click **Generate**.
5. Copy the **Service Principal** and **Secret**.

### Connect your Proofpoint TAP Account to Datadog

1. Add your Service Principal and Secret.
   | Parameters | Description |
   | ---------------------------- | ------------------------------------------------------------------------------------------- |
   | Service Principal | The Service Principal of your Proofpoint TAP account. |
   | Secret | The Secret of your Proofpoint TAP account. |
   | Get Click Blocked Events | Control the collection of Click Blocked Events from Proofpoint TAP. Enabled by default. |
   | Get Click Permitted Events | Control the collection of Click Permitted Events from Proofpoint TAP. Enabled by default. |
   | Get Message Blocked Events | Control the collection of Message Blocked Events from Proofpoint TAP. Enabled by default. |
   | Get Message Delivered Events | Control the collection of Message Delivered Events from Proofpoint TAP. Enabled by default. |
2. Click the Save button to save your settings.

## Data Collected

### Logs

The Proofpoint TAP integration collects and forwards click and message events to Datadog.

### Metrics

The Proofpoint TAP integration does not include any metrics.

### Events

The Proofpoint TAP integration does not include any events.

## Support

For any further assistance, contact [Datadog support][2].

[1]: https://www.proofpoint.com/uk/products/advanced-threat-protection/targeted-attack-protection
[2]: https://docs.datadoghq.com/help/

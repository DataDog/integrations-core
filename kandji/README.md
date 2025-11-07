## Overview

[Kandji][1] is an Apple device management and security platform that helps organizations automate deployment, enforce compliance, and secure macOS and iOS devices.

This integration ingests the following logs:
- **Audit**: Provides information about security events, device lifecycle changes, and admin/user actions.
- **Threats**: Provides information about detected threats, including classification, status, affected devices, associated files, processes, and blueprints.
- **Detections**: Lists detected findings, their severity, affected devices and applications, and associated blueprints.

Integrate Kandji with Datadog to gain insights into audit, and threats and detections logs using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating search and detailed insights. Additionally, the integration can be used for Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Prerequisites

- Kandji MDM, EDR and Vulnerability Management.

### Generate API Token from the Kandji Platform

1. Log in to Kandji Platform using **Admin** or **Owner** account and click on **Settings**.
2. Click the **Access** tab.
3. Scroll down to the **API Token** section and click the **Add Token** button. 
4. Enter **Name** and **Description** for your API token.
5. Click **Create**.
6. Copy the **Token**, then check the box confirming: **I have copied the token and understand that I will not be able to see these details again.**
7. Click **Next**.
8. Click **Configure** to manage the **API permissions** for a specific token.
9. Select **List Audit Events** and **Detections List**.
10. Click **Save**.
11. Under **API Token** section, locate your domain. For example, your organizations API Domain will be:
**your-subdomain.api.kandji.io**.

### Connect your Kandji Account to Datadog

1. Add your Domain and API Token.
   | Parameters | Description |
   | ---------- | ---------------------------------------------- |
   | Domain     | The Domain of your Kandji account.             |
   | API Token  | The API Token of your Kandji account.          |
2. Click the Save button to save your settings.

## Data Collected

### Logs

Kandji collects and forwards audit, and threat and detection logs to Datadog.

### Metrics

Kandji does not include any metrics.

### Events

Kandji does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.kandji.io/login/
[2]: https://docs.datadoghq.com/help/

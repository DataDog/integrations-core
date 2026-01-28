## Overview

[Iru][1] (formerly known as Kandji) is a unified, AI-powered IT and security platform that helps organizations protect users, applications, and devices by replacing multiple point solutions with a single, automated system.

This integration ingests the following logs:
- **Audit**: Provides information about security events, device lifecycle changes, and admin/user actions.
- **Threats**: Provides information about detected threats, including classification, status, affected devices, associated files, processes, and blueprints.
- **Detections**: Lists detected findings, their severity, affected devices and applications, and associated blueprints.

Integrate Iru(Kandji) with Datadog to gain insights into audit, and threats and detections logs using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating search and detailed insights. Additionally, the integration can be used for Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Generate API Token from the Iru(Kandji) Platform

1. Log in to Iru(Kandji) Platform using **Admin** or **Owner** account and click on **Settings**.
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

### Connect your Iru(Kandji) Account to Datadog

1. Add your Domain and API Token.
   | Parameters                   | Description                                         |
   | ---------------------------- | --------------------------------------------------- |
   | Domain                       | The Domain of your Iru(Kandji) account.             |
   | API Token                    | The API Token of your Iru(Kandji) account.          |
   | Collect Audit & Threat logs  | Control the collection of audit and threat logs from Iru(Kandji). Enabled by default.           |
   | Collect Detection logs       | Control the collection of detection logs from Iru(Kandji). Enabled by default.          |

2. Click the Save button to save your settings.

## Data Collected

### Logs

Iru(Kandji) collects and forwards audit, and threat and detection logs to Datadog.

### Metrics

Iru(Kandji) does not include any metrics.

### Events

Iru(Kandji) does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.iru.com/
[2]: https://docs.datadoghq.com/help/

# Agent Check: Microsoft Copilot

## Overview

[Microsoft Copilot][1] is an AI assistant integrated into Microsoft 365 applications such as Outlook, Word, Excel, PowerPoint, OneNote, and Teams. After a user in a Microsoft 365 organization is assigned a Copilot license, they can access Copilot through Copilot Chat or directly within supported Microsoft 365 applications.

By integrating Microsoft Copilot usage tracking with Datadog, you can ingest logs and metrics that reflect user activity and assess the value Copilot delivers within your Microsoft 365 environment.

With this integration, you can:
- Track user activity through logs that capture each user's last activity per Microsoft 365 application
- Identify Microsoft Copilot licenses that have not been used for extended periods
- Monitor real-time individual AI interactions using logs generated from [Microsoft Change Notifications for Copilot AI interactions][4]
- Receive alerts when Copilot AI guardrail responses spike

Microsoft computes Copilot usage reports with a delay of [up to 72 hours][3]. Real-time AI interaction logs are not affected by this delay. Upon detection of a new report, this integration:
- Submits metrics for active and enabled summary user counts per application
- Submits a log message for each user's last activity per application

## Setup

Connect a Microsoft 365 tenant to start tracking Copilot usage.

## Data Collected

### Logs

The Microsoft Copilot integration collects daily summary log messages for user Copilot activity and real-time log messages for individual AI interactions.

### Metrics

The Microsoft Copilot integration produces summary metrics representing active and enabled users of
Copilot per application once per day.

{{< get-metrics-from-git "microsoft-copilot" >}}

### Service Checks

Microsoft Copilot does not include any service checks.

### Events

Microsoft Copilot does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://copilot.microsoft.com/
[2]: https://docs.datadoghq.com/help/
[3]: https://learn.microsoft.com/en-us/microsoft-365/admin/activity-reports/microsoft-365-copilot-usage?view=o365-worldwide
[4]: https://learn.microsoft.com/en-us/microsoft-365-copilot/extensibility/api/ai-services/change-notifications/aiinteraction-changenotifications


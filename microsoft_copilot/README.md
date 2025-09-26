# Agent Check: Microsoft Copilot

## Overview

[Microsoft Copilot][1] is an AI assistant integrated into Microsoft 365, the cloud-based suite of productivity and communication tools that includes Microsoft Office applications. Once a user within the Microsoft 365 organization is assigned a Copilot license, they can access Copilot directly through Copilot Chat or through Microsoft 365 applications, including Outlook, Word, Excel, PowerPoint, OneNote, and Teams.

By integrating Microsoft Copilot usage tracking with Datadog, you can ingest and analyze user activity to gain insight into the value Microsoft Copilot delivers within your Microsoft 365 environment.

With this integration, you can:
- Track user activity through logs that capture each user's "last activity" per Microsoft 365 application.
- Identify the number of Microsoft Copilot licenses that have not been used for extended periods of time.

## Setup

Connect a Microsoft 365 tenant to start tracking Copilot usage.

## Data Collected

### Metrics

The Microsoft Copilot integration produces point-in-time metrics representing active and enabled users of Copilot per application.

{{< get-metrics-from-git "microsoft-copilot" >}}

### Service Checks

Microsoft Copilot does not include any service checks.

### Events

Microsoft Copilot does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://copilot.microsoft.com/
[2]: https://docs.datadoghq.com/help/


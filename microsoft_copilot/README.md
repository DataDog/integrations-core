# Agent Check: Microsoft Copilot

## Overview

[Microsoft Copilot][1] is an AI assistant component of Microsoft 365, a cloud-based suite of productivity and communication tools including Microsoft Office
applications. Once a user within the Microsoft 365 organization is assigned a Copilot license, Microsoft Copilot can be used directly via Copilot Chat or 
through the various Microsoft 365 applications, including Outlook, Word, Excel, PowerPoint, OneNote, and Teams.

By integrating Microsoft Copilot usage tracking with Datadog, you can ingest and analyze user activity that provides insight into the
value of Microsoft Copilot within your Microsoft 365 environment.

With this integration, you can:
- Track user activity via logs which capture individual user "last activity" per Microsoft 365 application.
- Identify the number of Microsoft Copilot licenses not being used for extended periods of time.

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


## Overview

[Asana][1] is a cloud-based work management tool designed to help individuals and teams keep track of tasks, delegate responsibilities, monitor progress, and communicate in real-time. By providing a centralized platform for collaboration, Asana helps teams stay organized and focused, ensuring that projects are completed on time.

This integration ingests the following logs:

- **Audit Logs**: Audit logs provide a detailed record of significant events, enabling your teams to identify and mitigate the impact of incidents as they arise, while also reviewing configuration changes with precision.

This integration gathers audit logs and forwards them to Datadog for seamless analysis. Datadog leverages its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. With preconfigured dashboards, the integration offers clear visibility into activities within the Asana platform. Additionally, it includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Generate API Credentials in Asana

1. Log in to your [Asana Admin Console][3] as a **Super Admin** of an Enterprise+ organization.
2. Navigate to the **Apps** tab in your Admin Console.
3. Click on **Service Accounts**.
4. Select the **Add Service Account** button and complete the following steps:
   1. Enter a descriptive and identifiable name under **Name**.
   2. Under **Permission Scopes**, select **Scoped permissions** and check the **Audit Logs** box.
5. Click **Save Changes** and copy the **Service Account PAT** for later use.
6. Go to the **Settings** tab in your Admin Console.
7. Scroll to the bottom of the page to locate the **Domain ID (Workspace ID)**.

### Connect your Asana Account to Datadog

1. Add your Workspace ID and Service Account PAT.
   | Parameters          | Description                                                                           |
   | ------------------- | ------------------------------------------------------------------------------------- |
   | Workspace ID        | The Workspace ID of your organization in the Asana platform.                          |
   | Service Account PAT | The Service Account Personal Access Token of your organization in the Asana platform. |

2. Click the Save button to save your settings.

## Data Collected

### Logs

The Asana integration collects and forwards audit logs to Datadog. For more details on the logs we collect with this integration, see the Asana Audit Logs API [Docs][4].

### Metrics

The Asana integration does not include any metrics.

### Events

The Asana integration does not include any events.

## Support

For any further assistance, contact [Datadog support][2].

[1]: https://asana.com/
[2]: https://docs.datadoghq.com/help/
[3]: https://app.asana.com/admin
[4]: https://developers.asana.com/docs/audit-log-events

## Overview

[Asana][1] is a cloud-based work management tool designed to help individuals and teams keep track of tasks, delegate responsibilities, monitor progress, and communicate in real-time. By providing a centralized platform for collaboration, Asana helps teams stay organized and focused, ensuring that projects are completed on time.

This integration ingests the following logs:

- Audit Logs: Audit logs offer a record of important events, empowering your teams to detect and minimize the impact of incidents when they occur, and scrutinize configuration edits.

This integration collects audit logs and sends them to Datadog for analysis. Datadog uses the built-in logs pipeline to parse and enrich these logs, enabling effortless search and analysis. The integration provides insight into activities on the Asana platform through the out-of-the-box dashboards. Also, This integration provides out of the box detection rules.

## Setup

### Configuration

#### Get Credentials of Asana

1. Log in to your [Asana admin console][3] as **super admin** of an Enterprise+ organization.
2. After logging in, click the **Apps** tab from your admin console.
3. Click **Service accounts**.
4. Click the **Add service account** button.
    1. Under **Name**, Enter a descriptive and identifiable service account name.
    2. Under **Permissions scopes**, choose **Scoped permissions**, and tick the **Audit logs** box.
5. Click **Save changes** and copy the **service account token** for later use.
6. Navigate to **Settings** tab from your admin console.
7. Scroll down till the end of the page, where you can find **Domain ID (Workspace ID)**.

#### Add your Asana Credentials

- Workspace ID
- Service Account PAT

## Data Collected

### Logs

The Asana integration collects and forwards audit logs to Datadog.

### Metrics

The Asana integration does not include any metrics.

### Events

The Asana integration does not include any events.

## Support

For any further assistance, contact [Datadog support][2].

[1]: https://asana.com/
[2]: https://docs.datadoghq.com/help/
[3]: https://app.asana.com/admin
# Agent Check: Workato

## Overview


[Workato][1] provides a platform for enterprise automation and integration so you can connect, integrate, and automate your applications, data, and processes end-to-end.

The Workato integration collects Jobs Logs (Recipe execution) and Status Metrics (Connection and Recipe state), sending them to Datadog for detailed analysis. The logs are parsed and enriched for efficient searching, while the metrics provide insights into operational status.

The integration includes a dashboard that shows Job execution status and duration, making it easier to monitor and understand trends and issues.

## Setup

### Generate API credentials in Workato

1. Log in to [Workato][2] as an administrator. 
2. Navigate to **Workspace Admin > API Clients**.
3. Click **Create API Client**, and then enter the required information:
   4. Under **Name**, Enter a descriptive and identifiable client name.
   5. Choose an appropriate **Client role** from the drop-down menu. Ensure the selected role has LIST and GET DETAILS permissions on all Workato Resources.
   6. Choose between _Selected Projects_ or _All Projects_ from the **Project access** drop-down menu.
   7. Leave the **Allowed IPs** text box blank to allow access from any IP.
8. Click **Create Client**, and copy the API token for later use.       

### Connect your Workato Account to Datadog

1. Add your Access Token
    |Parameters|Description|
    |--------------------|--------------------|
    |Access Token|Access token for your HubSpot private app.|
2. Click the Save button to save your settings.

## Data Collected

### Logs 

The Workato integration collects and forwards Activity logs to Datadog.

### Metrics

The HubSpot Content Hub integration collects and forwards Analytics metrics to Datadog.

{{< get-metrics-from-git "workato" >}}

### Service Checks

Workato does not include any service checks.

### Events

Workato does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.workato.com
[2]: https://app.workato.com/users/sign_in
[2]: https://app.datadoghq.com/account/settings/agent/latest

# Agent Check: Workato

## Overview


[Workato][1] provides a platform for enterprise automation and integration so you can connect, integrate,
and automate your applications, data, and processes end-to-end.

The Workato integration collects [jobs](https://docs.workato.com/en/recipes/jobs.html#viewing-job-reports), logs
(recipe execution), and status metrics (connection and recipe state), sending them to Datadog for detailed analysis.
The logs are parsed and enriched for efficient searching, while the metrics provide insights into operational status.

The integration includes a dashboard that shows job execution status and duration, making it easier to monitor and
understand trends and issues.

## Setup

### Generate API credentials in Workato

1. Log in to [Workato][2] as an administrator.
2. Navigate to the **Workspace Admin** > **API Clients** tab.
3. (Create a Client Role with sufficient permission) Click **Client Roles** tab.
4. Click **+ Add client role**.
   1. Check the following boxes to allow minimal read access:
   
        | Section  | Permission                                |
        |----------|-------------------------------------------|
        | Projects | Project Assets > List Projects            |
        | Projects | Project Assets > List Folders             |
        | Projects | Connections > List                        |
        | Projects | Recipes > List                            |
        | Projects | Recipes > Get job counts for recipes      |
        | Projects | Recipes > Get details                     |
        | Projects | Recipe Versions > List                    |
        | Projects | Jobs > List                               |
        | Projects | Jobs > Get job                            |
        | Admin    | Environment Management > Tags > List tags |
   2. Edit the role name, and click **Save changes**.
7. Select the **API Clients** tab.
8. Click **+ Add API Client**, and then enter the required information:
   1. Under **Name**, enter a descriptive and identifiable client name.
   2. Choose the newly created Client Role from the dropdown, or ensure the selected role has `LIST` and `GET DETAILS` permissions on all Workato Resources.
   3. If the Environments feature is enabled, choose the Environment to which this client has access.
   4. Choose between _Selected Projects_ or _All Projects_ from the **Project access** drop-down menu.
   5. Leave the **Allowed IPs** text box blank to allow access from any IP.
14. Click **Create Client**, and copy the API token for later use.

### Connect your Workato Account to Datadog

1. Add your Access Token
    |Parameters|Description|
    |--------------------|--------------------|
    |API Token|Token generated for your Workato API Client.|
2. Click the Save button to save your settings.

## Data Collected

### Logs

The Workato integration collects and forwards job execution results to Datadog.

### Metrics

The Workato integration produces point-in-time metrics representing recipe and connection state and forwards to Datadog.

{{< get-metrics-from-git "workato" >}}

### Service Checks

Workato does not include any service checks.

### Events

Workato does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.workato.com
[2]: https://app.workato.com/users/sign_in
[3]: https://app.datadoghq.com/account/settings/agent/latest

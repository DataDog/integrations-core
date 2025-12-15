# Databricks Integration

![Databricks default dashboard][21]

## Overview

Datadog offers several Databricks monitoring capabilities.

[Data Jobs Monitoring][25] provides monitoring for your Databricks jobs and clusters. You can detect problematic Databricks jobs and workflows anywhere in your data pipelines, remediate failed and long-running-jobs faster, and optimize cluster resources to reduce costs.

[Cloud Cost Management][26] gives you a view to analyze all your Databricks DBU costs alongside the associated cloud spend.

[Log Management][27] enables you to aggregate and analyze logs from your Databricks jobs & clusters. You can collect these logs as part of [Data Jobs Monitoring][25].

[Infrastructure Monitoring][28] gives you a limited subset of the Data Jobs Monitoring functionality - visibility into the resource utilization of your Databricks clusters and Apache Spark performance metrics.

[Reference Tables][32] allow you to import metadata from your Databricks workspace into Datadog. These tables enrich your Datadog telemetry with critical context like workspace names, job definitions, cluster configurations, and user roles.

[Data Observability][36] helps data teams detect, resolve, and prevent issues affecting data quality, performance, and cost. It monitors anomalies in volume, freshness, null rates, and distributions, and integrates with pipelines to correlate issues with job runs, data streams, and infrastructure events.

Model serving metrics provide insights into how your  Databricks model serving infrastructure is performing. With these metrics, you can detect endpoints that have high error rate, high latency, are over/under provisioned, and more.
## Setup

### Installation

First, [connect a new Databricks workspace](#connect-to-a-new-databricks-workspace) in Datadog's Databricks integration tile. Complete installation by configuring one or more capabilities of the integration: [Data Jobs Monitoring](#data-jobs-monitoring), [Cloud Cost Management](#cloud-cost-management), and [Model Serving](#model-serving). 

### Configuration
#### Connect to a new Databricks Workspace
<!-- xxx tabs xxx -->

<!-- xxx tab "Use a Service Principal for OAuth" xxx -->
<div class="alert alert-warning">New workspaces must authenticate using OAuth. Workspaces integrated with a Personal Access Token continue to function and can switch to OAuth at any time. After a workspace starts using OAuth, it cannot revert to a Personal Access Token.</div>

1. In your Databricks account, click on **User Management** in the left menu. Then, under the **Service principals** tab, click **Add service principal**.
2. Under the **Credentials & secrets** tab, click **Generate secret**. Set **Lifetime (days)** to the maximum value allowed (730), then click **Generate**. Take note of your client ID and client secret. Also take note of your account ID, which can be found by clicking on your profile in the upper-right corner. (You must be in the account console to retrieve the account ID. The ID will not display inside a workspace.)
3. Click **Workspaces** in the left menu, then select the name of your workspace.
4. Go to the **Permissions** tab and click **Add permissions**.
5. Search for the service principal you created and assign it the **Admin** permission.
6. In Datadog, open the Databricks integration tile.
7. On the **Configure** tab, click **Add Databricks Workspace**.
9. Enter a workspace name, your Databricks workspace URL, account ID, and the client ID and secret you generated.
<!-- xxz tab xxx -->

<!-- xxx tab "Use a Personal Access Token (Legacy)" xxx -->
<div class="alert alert-warning">This option is only available for workspaces created before July 7, 2025. New workspaces must authenticate using OAuth.</div>

1. In your Databricks workspace, click on your profile in the top right corner and go to **Settings**. Select **Developer** in the left side bar. Next to **Access tokens**, click **Manage**.
2. Click **Generate new token**, enter "Datadog Integration" in the **Comment** field, remove the default value in **Lifetime (days)**, and click **Generate**. Take note of your token.

   **Important:**
   * Make sure you delete the default value in **Lifetime (days)** so that the token doesn't expire and the integration doesn't break.
   * Ensure the account generating the token has [CAN VIEW access][30] for the Databricks jobs and clusters you want to monitor.

   As an alternative, follow the [official Databricks documentation][31] to generate an access token for a [service principal][31].

3. In Datadog, open the Databricks integration tile.
4. On the **Configure** tab, click **Add Databricks Workspace**.
5. Enter a workspace name, your Databricks workspace URL, and the Databricks token you generated.
<!-- xxz tab xxx -->

<!-- xxz tabs xxx -->

#### Data Jobs Monitoring 

1. Connect a workspace in Datadog's Databricks integration tile.
2. In the **Select products to set up integration** section, set **Data Jobs Monitoring** to **Enabled** to start monitoring Databricks jobs and clusters. 
3. See [the docs for Data Jobs Monitoring][33] to complete the configuration. 

**Note**: Ensure that the user or service principal being used [has the necessary permissions](#permissions) to access your Databricks cost data.

#### Cloud Cost Management 

1. Connect a workspace in Datadog's Databricks integration tile.
2. In the **Select products to set up integration** section, set **Cloud Cost Management** to **Enabled** to view and analyze Databricks DBU costs alongside the associated cloud cost. 

**Note**: Ensure that the user or service principal being used [has the necessary permissions](#permissions) to access your Databricks cost data.

#### Model Serving

1. Configure a workspace in Datadog's Databricks integration tile.
2. In the **Select resources to set up collection** section, set **Metrics - Model Serving** to **Enabled** in order to ingest model serving metrics.

#### Reference Table Configuration
1. Configure a workspace in Datadog's Databricks integration tile.
2. In the accounts detail panel, click **Reference Tables**.
3. In the **Reference Tables** tab, click **Add New Reference Table**.
4. Provide the **Reference table name**, **Databricks table name**, and **Primary key** of your Databricks view or table.

  * For optimal results, create a view in Databricks that includes only the specific data you want to send to Datadog. This means generating a dedicated table that reflects the exact scope needed for your use case.

5. Click **Save**.

#### Permissions
For Datadog to access your Databricks cost data in Data Jobs Monitoring or [Cloud Cost Management][34], the user or service principal used to query [system tables][35] must have the following permissions:
   - `CAN USE` permission on the SQL Warehouse.
   - Read access to the [system tables][35] within Unity Catalog. This can be granted with:
   ```sql
   GRANT USE CATALOG ON CATALOG system TO <service_principal>;
   GRANT SELECT ON CATALOG system TO <service_principal>;
   GRANT USE SCHEMA ON CATALOG system TO <service_principal>;
   ```
   The user granting these must have the `MANAGE` privilege on `CATALOG system`.

## Data Collected

### Metrics
#### Model Serving Metrics
See [metadata.csv][29] for a list of metrics provided by this integration.

### Service Checks

The Databricks integration does not include any service checks.
 
### Events

The Databricks integration does not include any events.

## Troubleshooting

You can troubleshoot issues yourself by enabling the [Databricks web terminal][18] or by using a [Databricks Notebook][19]. Need help? Contact [Datadog support][10].

[10]: https://docs.datadoghq.com/help/
[18]: https://docs.databricks.com/en/clusters/web-terminal.html
[19]: https://docs.databricks.com/en/notebooks/index.html
[21]: https://raw.githubusercontent.com/DataDog/integrations-core/master/databricks/images/databricks_dashboard.png
[25]: https://www.datadoghq.com/product/data-jobs-monitoring/
[26]: https://www.datadoghq.com/product/cloud-cost-management/
[27]: https://www.datadoghq.com/product/log-management/
[28]: https://docs.datadoghq.com/integrations/databricks/?tab=driveronly
[29]: https://github.com/DataDog/integrations-core/blob/master/databricks/metadata.csv
[30]: https://docs.databricks.com/en/security/auth-authz/access-control/index.html#job-acls
[31]: https://docs.databricks.com/en/admin/users-groups/service-principals.html#what-is-a-service-principal
[32]: https://docs.datadoghq.com/reference_tables
[33]: https://docs.datadoghq.com/data_jobs/databricks
[34]: https://docs.datadoghq.com/cloud_cost_management/
[35]: https://docs.databricks.com/aws/en/admin/system-tables/
[36]: https://docs.datadoghq.com/data_observability/
[8]: https://docs.datadoghq.com/integrations/spark/#metrics
[9]: https://docs.datadoghq.com/integrations/spark/#service-checks

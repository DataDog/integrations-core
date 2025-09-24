# Orca Security Integration For Datadog

## Overview

[Orca Security][1] is a cloud security platform that identifies, prioritizes, and remediates security risks and compliance. It provides features like real-time visibility, vulnerability management, workload protection, cloud security posture management, and compliance management.
This integration ingests the following log:

- Alert: Includes information such as the alert state, account details, the asset where the alert was detected, and additional details.

The Orca Security integration seamlessly ingests alert logs data using the built-in integration of Orca with Datadog. Before ingestion of the data, it normalizes and enriches the logs, ensures a consistent data format, and enhances information content for downstream processing and analysis. The integration provides insights into alert logs through the out-of-the-box dashboards.

**Minimum Agent version:** 7.59.1

## Setup

### Configuration

#### [Orca Security Configuration for Datadog][2]

1. Login to the Orca Security Platform.
2. Go to **Settings** > **Connections** > **Integrations**.
3. In the **SIEM/SOAR** section, select **Datadog**, and then click **Connect**.

   The Datadog Configuration window opens.
4. Specify the following settings:
   - **API Key** - Add the API key of your Datadog platform.
   - **Region** - Select the region where your Datadog instance is located.
5. Click **Save**.
6. Click **Configure** on the Datadog Integration and enable the integration.
7. Go to **Automations** and click **+ Create Automation**.
8. In the **Automation Details** section, provide **Automation Name**.
9. In the **Trigger Query** section, select all the values for alert state in the query. The query should look like this: `When an alert Alert State is open,in_progress,snoozed,dismissed,closed`
10. In the **Define Results** section, enable **Apply to Existing Alerts** if existing alerts in the Orca Security platform need to be forwarded to Datadog, or disable it to forward newly generated/updated alerts.  
**Note**: Alerts that were updated more than 18 hours ago cannot be ingested into Datadog.
11. In the **SIEM/SOAR** section under the **Define Results** section, check **Datadog** and select **Logs** as the Datadog type.
12. Click **Create**.

## Data Collected

### Logs

The Orca integration collects and forwards Orca alert logs to Datadog.

### Metrics

The Orca integration does not include any metrics.

### Events

The Orca integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://docs.orcasecurity.io/docs
[2]: https://docs.orcasecurity.io/docs/integrating-datadog
[3]: https://docs.datadoghq.com/help/

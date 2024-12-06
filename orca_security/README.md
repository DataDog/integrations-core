# Orca Security Integration For Datadog

## Overview

[Orca Security][1] a cloud security platform that identifies, prioritizes, and remediates security risks and compliance. It provides features like Real-time visibility, vulnerability management, workload protection, cloud security posture management, compliance management.
This integration ingests the following log:

- Alert: Represents details such as the state of alert, account details, asset in which the alert was found, and more.

The Orca Security integration seamlessly ingests the data of alert logs using the in-built integration of Orca with Datadog. Before ingestion of the data, it normalizes and enriches the logs, ensuring a consistent data format and enhancing information content for downstream processing and analysis. The integration provides insights into alert logs through the out-of-the-box dashboards.

## Setup

### Configuration

#### [Orca Security Configuration for Datadog][2]

1. Login to the Orca Security Platform.
2. Go to **Settings** > **Connections** > **Integrations**.
3. In the **SIEM/SOAR** section, select **Datadog**, and then click **Connect**.

   The Datadog Configuration window opens.
4. Specify the following settings:
   - **API Key** - Add API key of Datadog platform.
   - **Region** - Select the region where your Datadog instance is located.
5. Click **Save**.
6. Click **Configure** on the Datadog Integration and enable the integration.
7. Go to **Automations** and click **+ Create Automation**.
8. In the **Automation Details** section, provide **Automation Name**.
9. In the **Trigger Query** section, select all the values for alert state in the query. The query should look as below:

    ```When an alert Alert State is open,in_progress,snoozed,dismissed,closed```
10. In the **Define Results** section, please enable **Apply to Existing Alerts** if existing alerts in the Orca Security platform need to be forwarded to Datadog or disable it to forward newly generated/updated alerts. (**Note:** As per Datadog Log Ingestion behavior, alerts updated older than 18 hours cannot be ingested to Datadog.)
11. In the **SEIM/SOAR** under the **Define Results** section, check the **Datadog** and select **Logs** as the datadog type.
12. Click **Create**.

## Data Collected

### Logs

The Orca integration collects and forwards Orca Alert logs to Datadog.

### Metrics

The Orca integration does not include any metrics.

### Events

The Orca integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://docs.orcasecurity.io/docs
[2]: https://docs.orcasecurity.io/docs/integrating-datadog
[3]: https://docs.datadoghq.com/help/
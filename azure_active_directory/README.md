# Agent Check: azure_active_directory

## Overview

Azure Active Directory is a cloud hosted Active Directory offering by Microsoft Azure.
This integration allows you to ingest your [Azure AD activity logs][1] (Audit and SignIn logs) to Datadog.

## Setup

### Installation

This integration uses log forwarding from Azure using Event hub to Datadog and cofiguring Azure AD to forward activity logs to the event hub.

### Configuration

1. Setup the log forwarding pipeline from Azure to Datadog using Event Hub by following [directions here][2]

2. In Azure portal, Select Azure Active Directory > Monitoring > Audit logs.
   
3. Select Export Settings.

4. In the Diagnostics settings pane, do either of the following:

   - To change existing settings, select Edit setting.
   - To add new settings, select Add diagnostics setting. You can have up to three settings.

5. Select the Stream to an event hub check box, and then select Event Hub/Configure.

6. Select the Azure subscription and Event Hubs namespace that you created earlier to route the logs to.
   
7. Select OK to exit the event hub configuration.

8. Do either or both of the following:

   - To send audit logs, select the AuditLogs check box.
   - To send sign-in logs, select the SignInLogs check box.
    we recommend that you select both
  
9. Select Save to save the setting.

Logs should start coming into the platform after about 15 minutes.
For more details on the setup find [directions here][3]

## Data Collected

### Logs

This integration allows you to setup log ingestion for Azure Active Directory activity logs.

This inlcudes

   - Sign-ins – Provides information about the usage of managed applications and user sign-in activities

   - Audit logs - Provides traceability through logs for all changes done by various features within Azure AD.  

### Metrics

Azure Active Directory does not include any metrics.

## Troubleshooting

Need help? Contact [Datadog support][4].

[1]: https://docs.microsoft.com/en-us/azure/active-directory/reports-monitoring/overview-reports#activity-reports
[2]: https://docs.datadoghq.com/integrations/azure/?tab=eventhub#log-collection
[3]: https://docs.microsoft.com/en-us/azure/active-directory/reports-monitoring/tutorial-azure-monitor-stream-logs-to-event-hub
[4]: https://docs.datadoghq.com/help

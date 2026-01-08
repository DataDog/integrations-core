## Overview

Get alerts from SolarWinds Orion to aggregate and triage your alerts in a centralized location. 

This integration works by subscribing Datadog to all of your SolarWinds alert notifications.

**Minimum Agent version:** 7.67.0

## Setup

### Create trigger actions

To create a new trigger action in SolarWinds:

1. Navigate to **Alerts > Manage Alerts**.
2. Select any alert and click **Edit Alert**, or create a new alert if you do not have any.
3. Navigate to **Trigger Actions > Add Action**.
4. Select **Send a GET or POST Request to a Web Server**.
5. Click **Configure Action"**.
6. Fill in the Action Pane with the following details:

        a. **Name of Action**: Send Alert to Datadog (or whatever you prefer)
        b. **URL**: https://<YOUR-DC-INTAKE-URL>/intake/webhook/solarwinds?api_key=<DATADOG_API_KEY>
        c. **Select**: Use HTTP/S POST
        d. **Body to Post**: Copy and paste from alert template below
        e. **Time of Day**: Leave as is
        f. **Execution Settings**: Leave as is
        b. **URL**: https://app.datadoghq.com/intake/webhook/solarwinds?api_key=<DATADOG_API_KEY>
        c. **Select**: Use HTTP/S POST
        d. **Body to Post**: Copy and paste from alert template below
        e. **Time of Day**: Leave as is
        f. **Execution Settings**: Leave as is

7. Click **Add Action**.
8. Click the **Reset Actions** step and then repeat steps 4 - 7, using the _Reset Action_ template instead of the _Trigger Action_ template.
9. Click **Next**.
10. Click **Submit** on the ***Summary** page.

### Assign actions to alerts

1. From the Alert Manager view, select all the alerts you wish to send to Datadog, then navigate to **Assign Action > Assign Trigger Action**.
2. Select the _Send Alert to Datadog - Trigger_ action and click **Assign**.
3. Repeat for **Assign Action > Assign Reset Action** using the "Send Alert to Datadog - Reset" action.

### Trigger action body to post
``` 
{
    "acknowledged": "${N=Alerting;M=Acknowledged}",
    "acknowledged_by": "${N=Alerting;M=AcknowledgedBy}",
    "alert_description": "${N=Alerting;M=AlertDescription}",
    "alert_details_url": "${N=Alerting;M=AlertDetailsUrl}",
    "alert_id": "${N=Alerting;M=AlertDefID}",
    "alert_message": "${N=Alerting;M=AlertMessage}",
    "alert_name": "${N=Alerting;M=AlertName}",
    "alert_severity": "${N=Alerting;M=Severity}",
    "application": "${N=Generic;M=Application}",
    "device_type": "${N=SwisEntity;M=Router.Nodes.CustomProperties.Device_Type}",
    "host": "${N=SWQL;M=SELECT TOP 1 RelatedNodeCaption FROM Orion.AlertObjects WHERE AlertObjectID = ${N=Alerting;M=AlertObjectID} }",
    "host_url": "${N=SWQL;M=SELECT TOP 1 RelatedNodeDetailsUrl FROM Orion.AlertObjects WHERE AlertObjectID = ${N=Alerting;M=AlertObjectID} }",
    "ip": "${N=SwisEntity;M=IP_Address}",
    "location": "${N=SwisEntity;M=Router.Nodes.CustomProperties.City}",
    "object": "${N=SWQL;M=SELECT TOP 1 EntityCaption FROM Orion.AlertObjects WHERE AlertObjectID = ${N=Alerting;M=AlertObjectID} }",
    "object_type": "${N=Alerting;M=ObjectType}",
    "timestamp": "${N=SWQL;M=SELECT GETUTCDATE() as a1 FROM Orion.Engines}"
}
``` 

### Reset action body to post
``` 
{
    "acknowledged": "${N=Alerting;M=Acknowledged}",
    "acknowledged_by": "${N=Alerting;M=AcknowledgedBy}",
    "alert_description": "${N=Alerting;M=AlertDescription}",
    "alert_details_url": "${N=Alerting;M=AlertDetailsUrl}",
    "alert_id": "${N=Alerting;M=AlertDefID}",
    "alert_message": "${N=Alerting;M=AlertMessage}",
    "alert_name": "${N=Alerting;M=AlertName}",
    "alert_severity": "${N=Alerting;M=Severity}",
    "application": "${N=Generic;M=Application}",
    "device_type": "${N=SwisEntity;M=Router.Nodes.CustomProperties.Device_Type}",
    "host": "${N=SWQL;M=SELECT TOP 1 RelatedNodeCaption FROM Orion.AlertObjects WHERE AlertObjectID = ${N=Alerting;M=AlertObjectID} }",
    "host_url": "${N=SWQL;M=SELECT TOP 1 RelatedNodeDetailsUrl FROM Orion.AlertObjects WHERE AlertObjectID = ${N=Alerting;M=AlertObjectID} }",
    "ip": "${N=SwisEntity;M=IP_Address}",
    "location": "${N=SwisEntity;M=Router.Nodes.CustomProperties.City}",
    "object": "${N=SWQL;M=SELECT TOP 1 EntityCaption FROM Orion.AlertObjects WHERE AlertObjectID = ${N=Alerting;M=AlertObjectID} }",
    "object_type": "${N=Alerting;M=ObjectType}",
    "timestamp": "${N=SWQL;M=SELECT GETUTCDATE() as a1 FROM Orion.Engines}",
    "reset": "true"
}
``` 

## Data Collected

### Metrics

The SolarWinds integration does not include any metrics.

### Events

The SolarWinds integration collects SolarWinds alerts in the event stream.

### Service Checks

The SolarWinds integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help
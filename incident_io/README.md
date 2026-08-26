# Incident IO

## Overview

[incident.io][1] helps companies declare, collaborate, communicate around, and learn from events that disturb their normal course of business-from critical infrastructure being down, to data breaches and security incidents. It is a service that helps teams manage incidents and outages effectively. It typically provides features like incident reporting, tracking, and resolution workflows.

Integrate your incident.io account with Datadog to gain insights into incident-related activities.

## Setup

### Webhook Configuration

Configure the Datadog Event Management v2 webhook endpoint to forward incident.io incident events to Datadog. For more details, see the incident.io [webhooks][2] documentation.

1. Log in to your [incident.io account][3] as org owner.
2. Go to **Settings > Webhooks**.
3. Click **Add Endpoint**.
4. Fill in the following webhook URL, replacing `<DATADOG_API_KEY>` with your [Datadog API key][5]:
   ```
   https://event-management-intake.datadoghq.com/api/v2/events/webhook?dd-api-key=<DATADOG_API_KEY>&integration_id=incident-io
   ```
5. Select the type of incident events that you want to push to Datadog under the **Subscribe to events** section.
6. Click **Create**.

## Data Collected

### Events

The incident.io integration ingests the following events:

- Public incident events
- Private incident events
- Action and follow up events

### Metrics

incident.io does not include any metrics.

### Service Checks

incident.io does not include any service checks.

### Logs

incident.io does not include any logs.

## Support

Need help? Contact [Datadog support][4].

[1]: https://incident.io/
[2]: https://api-docs.incident.io/tag/Webhooks/
[3]: https://app.incident.io/
[4]: https://docs.datadoghq.com/help/
[5]: https://app.datadoghq.com/organization-settings/api-keys

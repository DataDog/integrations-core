## Overview

[incident.io][1] helps companies declare, collaborate, communicate around and learn from events that disturb their normal course of business - from critical infrastructure being down, to data breaches and security incidents. It is a service that helps teams manage incidents and outages effectively. It typically provides features like incident reporting, tracking, and resolution workflows.

Integrate your incident.io account with Datadog to gain insights into incident related activities.

## Setup

Follow the instructions below to configure this integration for your incident.io account.

### Configuration

#### Webhook Configuration
Configure the Datadog endpoint to forward events of incident.io incidents as logs to Datadog. See [incident.io webhook overview][2] for more details.

1. Select an existing API key or create a new one by clicking one of the buttons below: <!-- UI Component to be added by Datadog team -->
2. Log in to your [incident.io account][3] as org owner.
3. Go to **Settings > Webhooks**.
4. Click **Add Endpoint**.
5. Fill in the webhook URL that you generated in step 1.
6. Select the type of incident events that you want to push to Datadog under **Subscribe to events**.
7. Click **Create**.

## Data Collected

### Logs
The incident.io integration ingests the following logs:
- Public incident event logs
- Private incident event logs
- Action and follow up event logs 

### Metrics

incident.io does not include any metrics.

### Service Checks

incident.io does not include any service checks.

### Events

incident.io does not include any events.

## Support

Need help? Contact [Datadog support][4].

[1]: https://incident.io/
[2]: https://api-docs.incident.io/tag/Webhooks/
[3]: https://app.incident.io/
[4]: https://docs.datadoghq.com/help/


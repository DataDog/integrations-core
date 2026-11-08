## Overview

[Freshservice][1] is a cloud-based IT service management (ITSM) platform that helps teams handle tickets, changes, assets, and service requests.

This integration collects the following logs:

- **Audit logs**: Administrative changes to the account, such as changes to agents, groups, requesters, workflows, service level agreement (SLA) and operational level agreement (OLA) policies, ticket fields, sandboxes, and plans and billing. Entries from every workspace are included.
- **Ticket activities**: The activity history of every ticket updated in the account, including deleted tickets.

Use these logs to investigate administrative changes and to follow how tickets change over time.

**Note**: Audit logs require the Forest plan or the Audit Log add-on in Freshservice. On other plans, the integration still collects ticket activities and the tile shows a message about audit logs.

## Setup

### Prerequisites

- A Freshservice account on the Forest plan or with the Audit Log add-on, to collect audit logs.
- A dedicated Freshservice integration user with the **Account Admin** role. The role is required to read audit logs, and the user needs permission to view tickets in all workspaces. A dedicated user keeps the API key working when people leave your organization.
- If your Freshservice account restricts API access by IP address, allow Datadog's IP ranges. Find them in the [IP ranges][2] list.

### Create an API key in Freshservice

1. Log in to Freshservice as the integration user.
2. Click the profile picture in the upper right corner, then click **Profile Settings**.
3. In the right panel, click **View API Key** and complete the CAPTCHA.
4. Copy the API key.

API keys do not expire. Resetting the key in Freshservice, or deactivating the integration user, stops collection until you save the new key in Datadog.

### Configuration

Open the [Freshservice integration tile][3] in Datadog and add your credentials:

| Parameter | Description |
| --------- | ----------- |
| API key | The API key of the integration user. |
| Freshservice domain | Your Freshservice host name, such as `acme.freshservice.com`. |

Click **Save** to save your settings.

### Validation

After you save the account, logs appear in the [Log Explorer][4] with `source:freshservice`. The first logs can take up to 10 minutes to appear.

## Data Collected

### Logs

The Freshservice integration collects audit logs and ticket activities. Datadog tags these logs with `source:freshservice`.

Ticket activities are read through the Freshservice ticket APIs, which are rate limited per minute. On accounts with many updated tickets, collection can fall behind, and Datadog skips older ticket activity rather than collecting it late.

The integration does not collect the following:

- Activities of spam tickets
- Activities of Journey requests
- Agent sign-in events
- Activities of changes, problems, releases, and assets

### Metrics

The Freshservice integration does not include any metrics.

### Events

The Freshservice integration does not include any events.

### Service Checks

The Freshservice integration does not include any service checks.

## Uninstallation

1. Navigate to the [Freshservice integration tile][3] in Datadog and delete the account.
2. In Freshservice, deactivate the integration user, or reset its API key, to revoke Datadog's access.

## Support

For further assistance, contact [Datadog Support][5].

[1]: https://www.freshworks.com/itsm/
[2]: https://docs.datadoghq.com/api/latest/ip-ranges/
[3]: /integrations/freshservice
[4]: /logs?query=source%3Afreshservice
[5]: https://docs.datadoghq.com/help/

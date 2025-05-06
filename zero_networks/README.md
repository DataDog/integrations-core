# Zero Networks

## Overview

[Zero Networks][1] is a cybersecurity platform that enforces zero-trust principles by restricting access to network resources based on user identity and behavior. It automates the creation of security policies, ensuring that only authorized users and devices can connect, while blocking unauthorized attempts. With features like adaptive access control, audit logs, and micro-segmentation, it minimizes attack surfaces and protects against threats. The platform is easy to deploy and integrates seamlessly with existing systems.

This integration ingests the following logs:

- **Audit**: Records an event performed by the user, providing an overview of the event's timestamp, involved entities, actions, and more.
- **Network-Activities**: Represents information about network communication events occurring within a system, including protocol and traffic type, source and destination information, process information, user information, threat scores, and more.

This integration collects the listed logs and channels them into Datadog for analysis. These logs are parsed and enriched through the built-in logs pipeline, enabling effortless search and analysis. The integration provides insight into audit and network-activities through the out-of-the-box dashboards.

## Setup

### Generate API credentials in Zero Networks

1. Log in to the Zero Networks platform.
2. Navigate to **Settings**.
3. Under **Integrations**, click **API**.
4. Click **Add new token** and specify the settings of the new API key:
    - Token name: A meaningful name that can help you identify the API key.
    - Access type: The access permission assigned to the API key. Select **Read only**.
    - Expiry: The expiration duration of the API key. Select **36 months**.
5. Click **Add**.

### Connect your Zero Networks Account to Datadog

1. Add your Zero Networks credentials.

    | Parameters      | Description                                                  |
    | ----------------| ------------------------------------------------------------ |
    | Subdomain       | The subdomain from Zero Networks portal URL. For example, ```https://<sub_domain>.zeronetworks.com```.|
    | API Key         | The Personal API key of Zero Networks.                       |

2. Click **Save**.

## Data Collected

### Logs

The Zero Networks integration collects and forwards Zero Networks audit and network activities logs to Datadog.

### Metrics

The Zero Networks integration does not include any metrics.

### Service Checks

The Zero Networks integration does not include any service checks.

### Events

The Zero Networks integration does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://zeronetworks.com/
[2]: https://docs.datadoghq.com/help/

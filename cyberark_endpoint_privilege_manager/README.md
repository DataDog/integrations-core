## Overview

[CyberArk Endpoint Privilege Manager][1] enforces least privilege and enables organizations to block and contain attacks on endpoint computers, reducing the risk of information being stolen or encrypted and held for ransom. 

This integration ingests the following logs:

- **Raw Events**: Provides detailed records of endpoint activities captured by EPM agents, including threat detection events.
- **Policy Audit Events**: Provides detailed audit records which gives immediate picture of policy usage on endpoints.
- **Set Admin Audit Events**: Provides detailed audit records for actions carried out by EPM administrators within sets.
- **Account Admin Audit Events**: Provides detailed audit records for actions performed by account administrators.

Integrate CyberArk Endpoint Privilege Manager with Datadog to gain insights into raw events, policy adit events, set admin audit events, and account admin audit events  using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Additionally, the integration can be used for Cloud SIEM detection rules for enhanced monitoring and security.


## Setup

### Create a User in CyberArk Endpoint Privilege Manager
1. Log in to the CyberArk Endpoint Privilege Manager portal.
2. Navigate to **Administration**.
3. Open the **Account Management** section.
4. Click **Create** and then click on **Create User** from the dropdown.
5. Enter the following details:
   - Email
   - Password
   - Confirm Password
6. Select the **Account Administrator** checkbox and choose the **View Only** option.
7. Select **Allow to manage Sets** checkbox.
8. Click **Next**.
9. Assign the **View Only Set Admin** role for all listed sets.
10. Click **Finish**.


### Connect your CyberArk Endpoint Privilege Manager Account to Datadog

1. Add your `EPM Account Region`, `Username`, and `Password`.
   | Parameters | Description |
   | ---------- | ---------------------------------------------- |
   | EPM Account Region | The EPM Account Region of your CyberArk Endpoint Privilege Manager.|
   | Username | The Username of CyberArk Endpoint Privilege Manager account which has access to the available sets.|
   | Password | The CyberArk Endpoint Privilege Manager account password.|
2. Click **Save**.

## Data Collected

The CyberArk Endpoint Privilege Manager integration collects and forwards raw events, policy audit events, set admin audit events, and account admin audit events to Datadog.

### Metrics

The CyberArk Endpoint Privilege Manager integration does not include any metrics.

### Events

The CyberArk Endpoint Privilege Manager integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://www.cyberark.com/products/endpoint-privilege-manager/
[2]: https://docs.datadoghq.com/help/

## Overview

[CyberArk Endpoint Privilege Manager][1] enforces least privilege and enables organizations to block and contain attacks on endpoint computers, reducing the risk of information being stolen or encrypted and held for ransom. 

This integration ingests the following logs:

- **Raw Events**: Endpoint activities captured by EPM agents, including threat detection events.
- **Policy Audit Events**: Audit records of policy usage on endpoints.
- **Set Admin Audit Events**: Actions carried out by EPM administrators within sets.
- **Account Admin Audit Events**: Actions performed by account administrators.

Integrate CyberArk Endpoint Privilege Manager with Datadog to gain insights into raw events, policy audit events, set admin audit events, and account admin audit events using pre-built dashboard visualizations. Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Additionally, the integration can be used for Cloud SIEM detection rules for enhanced monitoring and security.


## Setup

### Create a Role and Assign a User in CyberArk Endpoint Privilege Manager

1. Log in to the CyberArk Endpoint Privilege Manager portal and navigate to **Administration**.
2. Open the **Roles** section and click **Create role**.
3. Enter the role details:
   - **Name**: Name of the role (e.g., *View Only Set Admin Role*)
   - **Permission groups**: Select `View Only Set Admin`
   - **Sets**: Select the required sets to collect data
4. Click **Create**.
5. Open the **Users** section and click **Add user**.
6. Enter the user details:
   - **User email**, **Password**, and **Confirm password**
7. Click **Add**.
   > A verification email is sent to the provided address. The user must open the email and click the verification link to activate the account before proceeding.
8. Open the **Role assignment** section, locate the newly created role, and click **Assign or unassign users** from its options menu.
9. Click **Assign users**, select the newly created user's email, click **Assign**.
10. Click **Save**.
11. Locate the **Account Admin ViewOnly Role**, and click **Assign or unassign users** from its options menu.
12. Click **Assign users**, select the newly created user's email, click **Assign**.
13. Click **Save**.


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

# PingOne Advanced Identity Cloud

## Overview

[PingOne Advanced Identity Cloud][1] is an identity-as-a-service (IDaaS) offering by Ping Identity that is deployed as a single-tenant host. It provides a range of services related to identity and access management (IAM), including single sign-on (SSO), multi-factor authentication (MFA), user management, and more.

This integration ingests the following [audit logs][2]:

- am-config: Represents all changes to configuration of the tenant environment, including OAuth client, journey, and application management.
- am-authentication: Represents all Journey activity as well as including administrative and internal component authentication activity.
- am-activity: Represents state changes to objects that were created, updated, or deleted by Advanced Identity Cloud end users.
- am-access (A filtered subset): Represents access request outcomes for the OAuth _authorize_ endpoint.
- idm-activity: Represents operations against internally managed users, groups, etc.

The PingOne Advanced Identity Cloud integration seamlessly collects audit logs using the REST APIs. With the out-of-the-box logs pipeline, the logs are parsed and enriched for easy searching and analysis. This integration includes a dashboard visualizing user journey, application, and administrator activity, and more.

## Setup

### Generate a Log API Key in PingOne Advanced Identity Cloud

1. As a tenant administrator, log into your PingOne Advanced Identity Cloud tenant.
2. From the profile dropdown in the upper-right corner, select **Tenant settings**.
3. Select the **Global Settings** tab on the **Tenant Settings** page.
4. Select **Log API Keys**, then the button **+ New Log API Key**.
5. In the dialog, provide a name for the API Key, then click on **Create key**.
5. Copy the `api_key_id` and `api_key_secret` values.

### Connect your PingOne Advanced Identity Cloud tenant to Datadog

1. Add your PingOne Advanced Identity Cloud domain and credentials.

    | PingOne Parameters | Description                                                                                         |
    |--------------------|-----------------------------------------------------------------------------------------------------|
    | Tenant Domain      | The fully-qualified domain name of the tenant, such as https://openam-tap-example.forgeblocks.com/. |
    | API Key ID         | The `api_key_id` obtained from the above instructions.                                              |
    | API Key Secret     | The `api_key_secret` obtained from the above instructions.                                          |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

This integration collects and forwards PingOne Advanced Identity Cloud audit logs to Datadog.

### Metrics

The PingOne integration does not include any metrics.

### Events

The PingOne integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://docs.pingidentity.com/pingoneaic/home.html
[2]: https://docs.pingidentity.com/pingoneaic/tenants/audit-debug-log-sources.html#log-source-descriptions
[3]: https://docs.datadoghq.com/help/

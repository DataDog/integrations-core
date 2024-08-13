# RingCentral

## Overview
The RingCentral integration seamlessly collects Voice, Audit, A2P SMS and Voice(Analytics) data and ingests them into Datadog for comprehensive analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration empowers users with deep insights into call activities, SMS trends, and audit trails through intuitive, out-of-the-box dashboards. Additionally, it includes pre-configured monitors for proactive notifications on SMS budget overrun and SMS error rates.

### The integration collects:

#### Logs for:
- Voice
- Audit

#### Metrics for:
- Voice (Analytics)
- A2P SMS

## Setup

### RingCentral Datadog Integration Configuration

Configure the Datadog endpoint to forward RingCentral logs and metrics to Datadog.

1. Navigate to `RingCentral`.
2. Add your [RingCentral credentials](#get-api-credentials-from-ringcentral).

| RingCentral Parameters                                                 | Description                                                                             |
|------------------------------                                          |-----------------------------------------------------------------------------------------|
| [Account ID](#ringcentral-account-id)                                  | The Account ID of RingCentral.                                                          |
| [Client ID](#ringcentral-application-client-id-and-client-secret)      | The Client ID of the RingCentral Application.                                           |
| [Client Secret](#ringcentral-application-client-id-and-client-secret)  | The Client Secret of the RingCentral Application.                                       |
| [JWT Token](#ringcentral-jwt-token)                                    | The JWT Token from RingCentral.                                                         |
| Get Voice Calls                                                        | Enable to collect Voice Call Logs from RingCentral. The default value is True.          |
| Get Voice(Analytics) Metrics                                           | Enable to collect Voice(Analytics) Metrics from RingCentral. The default value is True. |
| Get SMS Metrics                                                        | Enable to collect SMS Metrics from RingCentral. The default value is True.              |
| Get Audit Logs                                                         | Enable to collect Audit Logs from RingCentral. The default value is True.               |

### Get API Credentials from RingCentral

#### RingCentral Account ID
To access the Account ID, you need to first access details for a "Super Admin" user and then locate the Account ID through the URL:

1. Visit [RingCentral][1] and log in as a Super Admin.
1. Under the **Users** section, click **Users with Extensions**.
1. From the list of users, click on the user who has a "Super Admin" suffix in their name to open the user's details panel.
1. Look at the URL in your web browser's address bar.
1. Find the 9-digit number within the URL. This is your RingCentral Account ID.
   - **Example URL:** https://service.ringcentral.com/application/users/users/default/123456789/settings/default
   - The `123456789` is your Account ID.

#### RingCentral Application Client ID and Client Secret
To find the Cliend ID and Client Secret, you need to regester a new application:

1. Login to your [RingCentral Developer][2] account using a user with Super Admin role or [Custom role](#create-and-assign-a-custom-role). 
1. Click **Console**.
1. Under the *Apps* section, click **Register App**.
1. Select **Rest API app** for the App type .
1. Fill in the required details for your application, such as the name and description.
1. Select **No** for "Do you intend to promote this app in the RingCentral App Gallery?"
| Field     | Selection | 
| ---  | ----------- | 
| Do you intend to promote this app in the RingCentral App Gallery? | **No** |
| Auth type | **JWT auth flow** |
| Issue refresh tokens | **Yes** |
| Application scopes | Select the following:<br><ul><li>Analytics</li><li>Read Audit Trail</li><li>Read Call Log</li><li>A2P SMS</li>/ul> |
1. Click on create App.
1. After creating the application, find the `clientId` and `clientSecret` in the application settings. 
1. Copy these credentials. 
  **Note**: Ensure these credentials are stored securely and not exposed in public repositories or insecure locations.

#### RingCentral JWT Token
1. Login to [RingCentral Developers][2] with the same user you used to find the [Client ID and Client Secret](#ringcentral-application-client-id-and-client-secret).
1. Click **Credentials** under your username.
1. Click **Create JWT**.
1. Add an appropriate label and select the **Production** environment.
1. Allow this JWT token for only a specific app and add the `clientId` of the application created to find the [Client ID and Client Secret](#ringcentral-application-client-id-and-client-secret).
1. If you select an expiration date, make sure you create a new JWT and update it in the integration configuration before the expiry date.
1. Click **Create JWT**.

#### Create and assign a custom role
1. Create a custom role, following the [RingCentral documentation][3].
1. Select **Standard** role as a starting point.
1. Provide additional **Audit Trail** and **Company Call Log - View Only** permissions to the role.
1. Assign a custom role to a user, following the [RingCentral documentation][4].

## Data Collected

### Logs

The RingCentral integration collects and forwards Voice and Audit logs to Datadog.

### Metrics

The RingCentral integration collects and forwards Voice(Analytics) and SMS metrics to Datadog. See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The RingCentral integration does not include any events.

## Support

For further assistance, contact [Datadog Support][6].

[1]: https://service.ringcentral.com/
[2]: https://developers.ringcentral.com/
[3]: https://support.ringcentral.com/article-v2/10641-user-roles-permissions-edit-permission-custom-role.html?brand=RC_US&product=RingEX&language=en_US
[4]: https://support.ringcentral.com/article-v2/10647-user-roles-permissions-assign-role-user-details.html?brand=RC_US&product=RingEX&language=en_US
[5]: https://github.com/DataDog/integrations-core/blob/master/ringcentral/metadata.csv
[6]: https://docs.datadoghq.com/help/

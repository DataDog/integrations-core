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

### Get API Credentials from RingCentral

#### RingCentral Account ID

1. **Access User:**
   - Visit [RingCentral][1] and log in as a Super Admin.
   - Once logged in, go to the **Users** section.
   - Under the **Users** section, click on "Users with Extensions."
   - From the list of users, click on the user who has "Super Admin" suffix in their name. This will open the user's details panel.

2. **Locate the Account ID in the URL:**
   - Look at the URL in your web browser's address bar. The URL will contain a series of numbers.
   - Find the 9-digit number within the URL. This is your RingCentral Account ID.

   **Example URL:** https://service.ringcentral.com/application/users/users/default/123456789/settings/default

   The `123456789` is your Account ID.

#### RingCentral Application Client ID and Client Secret

1. **Register a New Application:**
   - Login to your [RingCentral Developer][2] account using a user with Super Admin role or Custom role (Refer [here][6] to create and assign a custom role).
   - Click on Console.
   - Under the Apps section, click on **Register App**.
   - Select the App type as **Rest API app**.
   - Fill in the required details for your application, such as the name and description.
   - Select "No" for "Do you intend to promote this app in the RingCentral App Gallery?"
   - Select the auth type as **JWT auth flow**.
   - Select "Yes" for "Issue refresh tokens?"
   - Select the following **Application scopes**:
     - Analytics
     - Read Audit Trail
     - Read Call Log
     - A2P SMS
   - Click on create App.

2. **Get the Client ID and Client Secret:**
   - After creating the application, you'll find the `clientId` and `clientSecret` in the application settings. Copy these credentials for the subsequent configuration steps.
   - Ensure these credentials are stored securely and not exposed in public repositories or insecure locations.

#### RingCentral JWT Token

- Login to [RingCentral Developers][2] with the same user as above and click on **Credentials** under your username.
- Click on **Create JWT**.
- Add an appropriate label and Select the **Production** environment.
- Allow this JWT token for only a specific app and add the `clientId` of the application created above.
- If you select an expiration date, ensure to create a new JWT and update it in the integration configuration before the expiry date.
- Click on **Create JWT**.

#### Create and assign a custom role

- Refer to this [link][5] to create a custom role.
- Select **Standard** role as a starting point.
- Provide additional **Audit Trail** and **Company Call Log - View Only** permissions to the role.
- To assign a custom role to a user, refer to this [link][7].

### RingCentral Datadog Integration Configuration

Configure the Datadog endpoint to forward RingCentral logs and metrics to Datadog.

1. Navigate to `RingCentral`.
2. Add your RingCentral credentials.

| RingCentral Parameters       | Description                                                                             |
|------------------------------|-----------------------------------------------------------------------------------------|
| Account ID                   | The Account ID of RingCentral.                                                          |
| Client ID                    | The Client ID of the RingCentral Application.                                           |
| Client Secret                | The Client Secret of the RingCentral Application.                                       |
| JWT Token                    | The JWT Token from RingCentral.                                                         |
| Get Voice Calls              | Enable to collect Voice Call Logs from RingCentral. The default value is True.          |
| Get Voice(Analytics) Metrics | Enable to collect Voice(Analytics) Metrics from RingCentral. The default value is True. |
| Get SMS Metrics              | Enable to collect SMS Metrics from RingCentral. The default value is True.              |
| Get Audit Logs               | Enable to collect Audit Logs from RingCentral. The default value is True.               |

## Data Collected

### Logs

The RingCentral integration collects and forwards Voice and Audit logs to Datadog.

### Metrics

The RingCentral integration collects and forwards Voice(Analytics) and SMS metrics to Datadog. See [metadata.csv][4] for a list of metrics provided by this integration.

### Events

The RingCentral integration does not include any events.

## Support

For further assistance, contact [Datadog Support][3].

[1]: https://service.ringcentral.com/
[2]: https://developers.ringcentral.com/
[3]: https://docs.datadoghq.com/help/
[4]: https://github.com/DataDog/integrations-core/blob/master/ringcentral/metadata.csv
[5]: https://support.ringcentral.com/article-v2/10641-user-roles-permissions-edit-permission-custom-role.html?brand=RC_US&product=RingEX&language=en_US
[6]: #create-and-assign-a-custom-role
[7]: https://support.ringcentral.com/article-v2/10647-user-roles-permissions-assign-role-user-details.html?brand=RC_US&product=RingEX&language=en_US
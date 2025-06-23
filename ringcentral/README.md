# RingCentral

## Overview

[RingCentral][5] is a leading cloud-based communication and collaboration platform for businesses. It offers services such as voice, messaging, and video conferencing, seamlessly integrating with various business applications.

The RingCentral integration collects voice and audit logs, as well as Voice (Analytics) and A2P SMS metrics, and sends them to Datadog for comprehensive analysis.

## Setup

### Generate API Credentials in RingCentral

1. Log into your [RingCentral Developer][2] account using a user with a Super Admin role or [Custom role](#create-and-assign-a-custom-role).  
2. Click **Console**.
3. Under the *Apps* section, click **Register App**.
4. Select **Rest API app** for the App type .
5. Fill in the required details for your application, such as the name and description.

   | Field     | Selection | 
   | ---  | ----------- | 
   | Do you intend to promote this app in the RingCentral App Gallery? | **No** |
   | Auth type | **JWT auth flow** |
   | Issue refresh tokens | **Yes** |
   | Application scopes | Select the following: Analytics, Read Audit Trail, Read Call Log, A2P SMS|
6. Click on Create App.
7. After creating the application, find the `clientId` and `clientSecret` in the application settings.
8. To get the JWT Token, locate the **Credentials** by clicking your username in the top-right corner.
9. Click **Create JWT**.
10. Add an appropriate label and select the **Production** environment.
11. Allow this JWT token for only a specific app and add the `clientId` of the application created above.
12. If you select an expiration date, make sure you create a new JWT and update it in the integration configuration before the expiry date.
13. Click **Create JWT**.


#### Create and assign a custom role
1. Create a custom role, following the [RingCentral documentation][3].
2. Select **Standard** role as a starting point.
3. Provide additional **Audit Trail** and **Company Call Log - View Only** permissions to the role.
4. Assign a custom role to a user, following the [RingCentral documentation][4].


### Get RingCentral account ID
1. Visit [RingCentral][1] and log in as a Super Admin.
2. Under the **Users** section, click **Users with Extensions**.
3. From the list of users, click on the user who has a "Super Admin" suffix in their name to open the user's details panel.
4. Look at the URL in your web browser's address bar.
5. Find the 9-digit number within the URL. This is your RingCentral account ID.
   - **Example URL:** https://service.ringcentral.com/application/users/users/default/123456789/settings/default
   - The `123456789` is your Account ID.


### Connect your RingCentral account to Datadog

1. Add your RingCentral credentials.

   | Parameters       |   Description                                                 |
   | ---------------  | --------------------------------------------------------------|
   |Account ID        | The account ID of RingCentral.                                |
   |Client ID         | The client ID of the RingCentral application.                 |
   |Client Secret     | The client secret of the RingCentral application.             |
   |JWT Token         | The JWT token from RingCentral.                               |
   |Get Voice Calls Logs  | Enable to collect voice call logs from RingCentral. The default value is "true". |
   |Get Voice(Analytics) Metrics | Enable to collect Voice(Analytics) metrics from RingCentral. The default value is "true". |
   |Get SMS Metrics    | Enable to collect SMS metrics from RingCentral. The default value is "true".  | 
   |Get Audit Logs     | Enable to collect audit logs from RingCentral. The default value is "true".   |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The RingCentral integration collects and forwards Voice and Audit logs to Datadog.

### Metrics

The RingCentral integration collects and forwards Voice(Analytics) and SMS metrics to Datadog.

{{< get-metrics-from-git "ringcentral" >}}

### Events

The RingCentral integration does not include any events.

## Support

For further assistance, contact [Datadog Support][6].

[1]: https://service.ringcentral.com/
[2]: https://developers.ringcentral.com/
[3]: https://support.ringcentral.com/article-v2/10641-user-roles-permissions-edit-permission-custom-role.html?brand=RC_US&product=RingEX&language=en_US
[4]: https://support.ringcentral.com/article-v2/10647-user-roles-permissions-assign-role-user-details.html?brand=RC_US&product=RingEX&language=en_US
[5]: https://www.ringcentral.com/
[6]: https://docs.datadoghq.com/help/

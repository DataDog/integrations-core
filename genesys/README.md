# Genesys

## Overview

[Genesys][1] is a comprehensive cloud-based contact center platform that enables businesses to manage and optimize customer interactions across multiple channels, including voice, chat, email, social media, and messaging. It's known for its flexibility, scalability, and integration capabilities, helping businesses improve customer experience and streamline operations.

The Genesys integration collects conversations (Voice, Email, Message, Callback, Chat) analytics metrics and audit logs and ingests them into Datadog for comprehensive analysis.

## Setup

### Generate Client ID and Client Secret config parameters in Genesys
1. Login to your [Genesys account][2] with **Admin** role.
2. [Add a new role][3] with the following permissions:
    1. Analytics > Conversation Aggregate > View (Query for conversation aggregates)
    2. Analytics > Conversation Detail > View (Query for conversation details)
    3. Audits > Audit > View (View audits)
3. Ensure the role created in the previous step is assigned to the logged-in user. For more information on assigning roles to users, see the Genesys guide to [Assign roles, divisions, licenses, and add-ons][4].
4. Navigate to **Admin > Integrations > OAuth** section.
5. Click **Add Client**.
6. Enter an appropriate name.
7. Select **Client Credentials** as the Grant Type.
8. Click the **Roles** tab and assign the role created in step 2.
9. Click **Save**.
10. Copy the Client ID and Client Secret from the **Client Details** Tab. 

### Connect your Genesys Account to Datadog

1. Add your Client ID and Client Secret

    |Parameters| Description                                                                                    |
    |--------------------|------------------------------------------------------------------------------------------------|
    |Client ID| Client ID for your Genesys account.                                                        |
    |Client Secret| Client Secret for your Genesys account.                                                 |

2. Click the Save button to save your settings.

## Data Collected

### Logs 
The Genesys integration collects and forwards audit logs to Datadog.

### Metrics

The Genesys integration collects and forwards conversation analytics metrics to Datadog. See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The Genesys integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][6].

[1]: https://www.genesys.com/genesys-cloud
[2]: https://apps.mypurecloud.com/
[3]: https://help.mypurecloud.com/articles/add-roles/
[4]: https://help.mypurecloud.com/articles/assign-roles-divisions-licenses-and-add-ons/#citem_3b80-08e1
[5]: https://github.com/DataDog/integrations-core/blob/master/genesys/metadata.csv
[6]: https://docs.datadoghq.com/help/
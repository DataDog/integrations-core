# Okta Workflows

## Overview
[Okta Workflows][1] is a no-code automation platform provided by Okta, designed to simplify and automate identity-related tasks and processes. It allows organizations to build custom workflows that integrate seamlessly with Okta's identity and access management capabilities and third-party applications, enhancing operational efficiency, security, and user experience.

The Okta Workflows integration collects Okta workflow event logs and sends them to Datadog for comprehensive analysis.

## Setup

### Generate API Credentials in Okta Workflows
You can connect Okta Workflows to Datadog using one of the following authentication methods:

#### Option A: Using OAuth
1. Log in to the [Okta Admin Console][2].
2. Navigate to **Applications** > **API Services Integrations** > **Add Integrations** > **Datadog**.
3. Upon installation, you will be provided with a set of client ID and client secret credentials. Copy these credentials.

#### Option B: Using an API Token
1. Log in to the [Okta Admin Console][2] as a user with the [Read-only administrators][3] role.
2. Follow the steps in [this guide][5] to generate an API token.

### Get Okta Workflows Domain
1. Sign in to your Okta organization with your administrator account.
2. Locate the **Domain** by clicking your username in the top-right corner of the Admin Console. The domain appears in the dropdown menu. Your Okta domain looks like:
     - example.oktapreview.com
     - example.okta.com
     - example.okta-emea.com

### Connect your Okta Workflows Account to Datadog
1. Select an authorization method, and based on your chosen method, provide the following parameters:

   #### If using OAuth:
   | Parameters           | Description                         |
   |--------------------- |-----------------------------------  |
   | Okta Domain          | Domain of your Okta Workflow        |
   | Client ID            | Client ID for your Okta account     |
   | Client Secret        | Client Secret for your Okta account |

   #### If using API Token:
   | Parameters           | Description                         |
   |--------------------- |-----------------------------------  |
   | Okta Domain          | Domain of your Okta Workflow        |
   | API Key              | The API Key for your Okta Workflow  |


2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The Okta Workflows integration collects and forwards Okta workflow event logs to Datadog.

### Metrics

The Okta Workflows integration does not collect any metrics.

### Events

The Okta Workflows integration does not include any events.

## Support

For further assistance, contact [Datadog Support][4].

[1]: https://www.okta.com/products/workflows/
[2]: https://login.okta.com/
[3]: https://help.okta.com/en-us/content/topics/security/administrators-read-only-admin.htm
[4]: https://docs.datadoghq.com/help/
[5]: https://help.okta.com/en-us/content/topics/security/api.htm?cshid=ext-create-api-token#create-okta-api-token

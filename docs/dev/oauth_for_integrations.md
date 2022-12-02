---
title: OAuth for Integrations
kind: documentation
---

{{< beta-callout btn_hidden="true" >}}
  The Datadog Developer Platform is currently in beta. If you don't have access, contact apps@datadoghq.com.
{{< /beta-callout >}} 

## Overview

OAuth enables users to authorize third-party integrations with access to specific scopes of users' Datadog data. This authorization allows integrations to push data into Datadog and pull data out from Datadog. For example, if a user authorizes an integration for read access to their Datadog monitors, the integration can directly read and extract their monitor data. 

For more information on Datadog’s OAuth implementation, see the [Datadog OAuth2 documentation][1].

## Use OAuth in an integration 

OAuth allows Datadog customers to easily and securely authorize third-party platforms through a couple of clicks—without having to directly input API or app keys anywhere. You can use OAuth with existing integrations or configure OAuth as a part of developing new integrations.  

When building an integration with OAuth, you can select the exact scopes of data that your application needs access to, and the customer can grant access to the granular scopes that you’ve requested. While optional scopes are not supported, all scopes requested by an integration become accessible when a customer authorizes it. 

## Build an integration with OAuth

This section describes how to build a new integration with a tile on the [Marketplace][2] or [Integrations][3] page. If you’re building upon an existing integration, or building a new integration and want to add it to an existing tile on either page, see [Adding OAuth to an existing offering](#Adding-oauth-to-an-existing-offering).

### Create an app from a template

1. Navigate to the [Datadog Developer Platform][4] and click **+New App**. 

   You need to create an app for each integration OAuth client. Datadog ties this app to your integration once your integration is published.

2. Select a **Blank App** and add a name for your app. 
3. Click **Create**.
4. In the **Basic Information** tab, complete the fields that populate in the details view.
5. Once you are ready to publish your OAuth client, click the **Mark Stable** button. 
6. Click **Save**.

### Create an OAuth client

The client is the component of an application that enables users to authorize the application access to the customer's Datadog data. In order to gain access, the client requires the appropriate access token.

1. Navigate to the **OAuth & Permissions** tab under **Features** and click **Create OAuth Client**.

   The OAuth clients you create for integrations are **confidential clients** that provide a client ID and client secret. The client you create in this step is a private version of the client, whose credentials you can use for testing. When a published version of this client is created, you will receive a new set of credentials. **These credentials are never shown again after you create the client, so be sure to store them in a secure location.**

2. Enter your client information such as the name, description, redirect URIs, and onboarding URL. 
3. Configure scopes for the OAuth client by searching for scopes and selecting their checkboxes in the **Requested** column. 
    
   Scopes determine the types of data your app can access in the customer's Datadog account. This allows your integration to access the necessary scopes. Only request the minimum amount of scopes required for your use case, as more can be added later on as needed.

   In order to submit data into Datadog, the `api_keys_write` scope must be selected. This is a private scope that is only approved for integration partners and allows you to create an API key on the user’s behalf, which you can use to send data into Datadog. 

4. Click **Save Changes**.
5. After creating an OAuth client and assigning it scopes, you can implement the OAuth PKCE protocol in your integration, complete the authorization code grant flow, and start writing integration code utilizing the endpoints available through OAuth.

   In the authorization code grant flow, you receive an authorization code and refresh token, then exchange the code for an access token that can be used to access the data you want to pull from Datadog. 

   For more information about implementing the OAuth protocol with Datadog, see [Datadog OAuth2][1]. For more information about building and publishing an integration, see the [Integrations developer documentation][5].

6. Test the OAuth protocol by clicking **Test Authorization** on your client's details page. This directs you to the onboarding URL and starts the authorization flow that a customer takes. 

    Before your client is published, only members of your Datadog organization can authorize against your client during testing. 

7. To validate that OAuth is working properly, make a request to the `marketplace_create_api` endpoint with your token in the headers of the request. 

   If successful, this request returns an API key that you should securely save so you can use it to submit data into Datadog on behalf of the user. **You cannot access this API key value again after the initial request response**.

8. Test that your OAuth client can work across multiple [Datadog sites][8] by kicking off authorization from a non-US1 Datadog account:
   - If you do not have access to a sandbox account on a different site, contact `marketplace@datadog.com`. 
   - Export your app manifest from the account in the *original* Datadog site by navigating to the app you've created in the Developer Platform, clicking the gear icon on the top right, and clicking **Export App Manifest**. 
   - In your account on the *new* Datadog site, navigate to the Developer Platform and import your app manifest from Step 2.
   - After successfully importing your manifest, navigate to the **OAuth & Permissions** tab to find your OAuth client, along with its client ID and client secret. Use these credentials to test authorization from this site. 

9. Test any additional scopes that you’ve requested access for.

### Publish the OAuth client

In order to publish an OAuth client, you first need to open a pull request for your integration in either the [`integrations-extras`][5] or [Marketplace][6] GitHub repositories. 

As a part of your pull request, update your README file with an **uninstallation** section under `## Setup` that includes the following instructions (along with any custom instructions you would like to add):

- Once this integration has been uninstalled, any previous authorizations are revoked. 
- Additionally, ensure that all API keys associated with this integration have been disabled by searching for the integration name on the [API Keys page][10].


To start the publishing process in the [Developer Platform][4]:

1. Navigate to the **Publishing** tab under **General**. In Step 1 of the publishing flow, you receive your published client ID and secret. In Step 2, you can enter additional information about your integration and see the published `app_uuid` to use below.

   Save your client ID, client secret, and `app_uuid` in a secure location. 

2. When opening a pull request for a **new integration** in `integrations-extras` or `Marketplace`, use the `app_uuid` value for publishing in the `app_uuid` field of the `manifest.json` file. If the `app_uuid` values do not align, your application does not publish correctly. If you have an **existing integration**, there is no need to update the `app_uuid`.

You cannot edit a published OAuth client directly, so only go through the publishing flow when everything has been tested and is ready to go. To make updates to the OAuth client, you need to go through the publishing flow again. **The published client credentials do not appear again**.

For more information about the integration publishing process, see the [Marketplace and Integrations documentation][7]. 

## Add OAuth to an existing offering

The process for adding an OAuth client to an existing integration is similar to what is outlined above, with some key differences.

### If you have an existing integration that’s not connected to a UI Extension

Follow the [steps](#build-an-integration-with-oauth) above, and ensure that you open a pull request to add new uninstallation instructions to your integration tile.

There's no need to change your `app_uuid` in the `manifest.json` file if you have an existing integration.

### If you have an existing integration that’s currently connected to a UI Extension (shares the same tile)

Instead of creating an app, navigate to the app that includes your published UI Extension in the Developer Platform and follow the remaining [steps](#create-an-oauth-client). 

Once you’ve created your integration's OAuth client and are ready for publishing, click **Edit** on your app and navigate to the **Publishing** tab under **General**. Ensure that you also open a pull request to add new uninstallation instructions to your tile.

**Note**: There's no need to change your `app_uuid` in the `manifest.json` file if you have an existing integration or UI Extension.

### If you have a published UI Extension and want to add an integration to the same tile

Instead of creating an app, navigate to the app that includes your published UI Extension in the Developer Platform and follow the remaining [steps](#create-an-oauth-client).

Open a pull request to update your existing tile with additional information about your integration—including updates to the README, image folder, and more. Add a link to this pull request during the publishing process.

## Further Reading

Additional helpful documentation, links, and articles:

- [OAuth 2.0 in Datadog][1]
- [Authorize your Datadog integrations with OAuth][11]

[1]: https://docs.datadoghq.com/developers/authorization/oauth2_in_datadog/
[2]: https://app.datadoghq.com/marketplace
[3]: https://app.datadoghq.com/integrations
[4]: https://app.datadoghq.com/apps
[5]: https://github.com/DataDog/integrations-extras/
[6]: http://github.com/DataDog/marketplace
[7]: https://docs.datadoghq.com/developers/marketplace/#develop-your-offering
[8]: https://docs.datadoghq.com/getting_started/site/
[9]: https://app.datadoghq.com/organization-settings/oauth-applications
[10]: https://app.datadoghq.com/organization-settings/api-keys
[11]: https://www.datadoghq.com/blog/oauth/

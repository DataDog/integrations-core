---
title: OAuth for Data Integrations
kind: documentation
---

## What is OAuth? 

OAuth provides a way for customers to authorize third-party integrations to access specific scopes of their Datadog data. This authorization allows integrations to push data into Datadog, and pull data out from Datadog. For example, if a user authorizes an integration for read access to their Datadog monitors, the integration will be able to directly read and extract their monitor data. For more information on Datadog’s OAuth implementation, see the [Datadog OAuth2 documentation][1].

## Why use OAuth in a data integration? 
OAuth allows Datadog customers to easily and securely authorize third-party platforms through the click of a button and without having to directly input their API or App key anywhere. When building an integration with OAuth, you can select the exact scopes of data that your application needs access to, and the customer will be able to grant access to the granular scopes that you’ve requested.  

Note that optional scopes are not supported - all scopes requested by an integration will be accessible once authorized by the customer.

You can use OAuth with existing data integrations, or configure OAuth as a part of developing new data integrations.  


## Building a new data integration with OAuth
These steps outline the process for building a new data integration that will have its own tile on the Marketplace or Integrations page. If you’re building a new data integration and want to add it to an existing tile on either page, see [Adding OAuth to an existing offering](##Adding-oauth-to-an-existing-offering).


1. Create a new app in the [Datadog Developer Platform][2]

    A new app is needed for each integration OAuth client. Datadog ties this app to your integration once your integration is published.

    - The Developer Platform is currently in beta. If you don’t have access, please contact apps@datadog.com.

    - Once inside the Developer Platform, click **New App**. You are prompted to fill out a couple fields describing your app - these are all internal-only and will not be made public. 

2. Create an OAuth Client

    The client is the component of the application that requires access to the customer’s Datadog data. To gain access, the client must hold the appropriate access token. 


    - Navigate to the **OAuth and Permissions** tab within the Developer Platform, and click **New Confidential OAuth Client**.
    
    - All OAuth clients created for data integrations are **confidential** clients that provide a client ID and client secret. The client you create in this step is a private version of the client, whose credentials you can use for testing. A published version of this client will be created during the publishing flow (step 6), and you will receive a new set of credentials. **The credentials WILL NOT be shown again after you create the client, so be sure to store them in a secure location.**

    - Enter your client information such as the name, description, client role (integration), redirect URIs, and onboarding URL. 

3. Configure Scopes for your OAuth client
    
    Scopes determine the types of data from the customer's Datadog account that your application can access.

    - Under Permissions, you can search for and select the scopes that will need to be accessed by your integration.

    - Be sure to only request the minimum amount of scopes required for your use case, as more can be added later on if needed.

    - **Note**: In order to submit data into Datadog, the `api_keys_write` scope must be selected. This is a private scope only approved for integration partners that allows you to create an API Key on the user’s behalf, which you can then use to send data into Datadog. 

4. Implement the OAuth PKCE protocol in your integration

    Now that you’ve created a client and assigned scopes, you can implement the OAuth protocol, go through the Authorization Code Grant Flow, and begin writing integration code that utilizes the endpoints made available through OAuth. The Authorization Code Grant Flow revolves around receiving an authorization code and refresh token and exchanging it for an access token that can be used to access the data that you’d like to pull from Datadog. 


    See [Datadog OAuth2 documentation - OAuth Flow Overview][1] for more details on implementing the OAuth protocol with Datadog.


    See the [integration developer documentation][3] for more details on building and publishing an integration.

5. Test the OAuth protocol

    During testing (before your client is published), only members of your Datadog organization can authorize against your client. 


    - You can begin testing by clicking **Test Authorization** on your client details page within the Developer Platform. This will take you to the onboarding URL and kick off the same authorization flow that the customer will take. 

    - To validate that OAuth is working properly, make a request to the `marketplace_create_api` endpoint, with your token in the headers of this request. If successful, this request returns an API key that you should securely save, so that you can use it to submit data into Datadog on behalf of the user.  You will not be able to access this API Key value again after the initial request response.

    - Be sure to also test out the other scopes to which you’ve requested access.

6. Publish the OAuth client

    In order to publish an OAuth client, you’ll need to open a pull request for your data integration in either the integrations-extras or marketplace GitHub repositories. To learn more about the integration publishing process, see our [Marketplace and Integrations documentation][3]. 

    - To start the publishing process, navigate to the **Publishing** tab within the Developer Platform. You’ll receive your published client ID and client secret, as well as your `app_uuid` to use for publishing (**reminder: save these values in a secure location**), and you will be prompted to fill out some information about your integration. 

    - When opening a Pull Request, you MUST use the `app_uuid` value for publishing as the `app_uuid` value in the manifest.json file, or your app will not be published correctly.

    - **Note:** you cannot edit a published OAuth client directly, so only go through the publishing flow when everything has been tested and is ready to go. To make updates to the OAuth client, you will need to go through the publishing flow again, and the published client credentials will not show up again).

## Adding OAuth to an existing offering
The process for adding an OAuth client to an existing integration is similar to what is outlined above, with a few key differences.

### If you have an existing data integration that’s not connected to a UI Extension:
Follow the steps as written above. This will not require a new pull request on the integrations-extras or marketplace repository - instead you’ll add a link to your existing file directory in the marketplace or integrations-extras repository during the publishing process. 

### If you have an existing data integration that’s currently connected to a UI Extension (shares the same tile):
Instead of creating a new app as specified in Step 1 above, navigate to the app within the Developer Platform that includes your published UI Extension, and follow the rest of the steps as written.

You will need to open a new pull request to update the `app_uuid` field in the manifest.json file. After you’ve created your data integration OAuth client and are ready for publishing, navigate to the Publishing tab, which will take you through a few steps and provide you with an `app_uuid` to use for publishing. This value is what should be used as the `app_uuid` in the manifest.json file. 

### If you have a published UI Extension and are adding a new data integration to the same tile: 
Instead of creating a new app as specified in Step 1 above, navigate to the app within the Developer Platform that includes your published UI Extension, and follow the rest of the steps as written.

You will need to open a new pull request to update your existing tile with your integration code (if it’s an agent-based integration), as well as new information about your integration in your readme, images, etc. Please share a link to this new pull request during the publishing process.

[1]: <link to datadog oauth2 docs>
[2]: https://app.datadoghq.com/apps
[3]: https://docs.datadoghq.com/developers/marketplace/#develop-your-offering
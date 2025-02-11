# Sanity

## Overview

[Sanity][1] is a headless content management system (CMS) designed for building flexible, real-time websites and applications. It enables developers and content teams to efficiently manage structured content across multiple platforms.

Integrate Sanity with Datadog to gain insights into content and project-related activity logs through the Sanity API and GROQ-powered Webhook. Pre-built dashboard visualizations provide immediate insights into Sanity activity logs.

## Setup

### Generate API Token in Sanity

1. Log in to your [Sanity account][2] as an Administrator. You are automatically redirected to the [manage page][3].
2. Select your project.
3. In the navigation panel, click **API**.
4. In the left sidebar, select **Tokens**.
5. Click **Add API Token**.
6. Enter a name and set the permission to **Viewer**.
7. Click **Save** to copy a newly generated token.

### Connect your Sanity account to Datadog

1. Add your Sanity API Token    
    |Parameters|Description|
    |--------------------|--------------------|
    |API Token|API Token of your Sanity project.|

2. Click the **Save** button to save your settings.

**Note**: These steps enable collection of project activity logs.

### Webhook Configuration
Configure the Datadog endpoint to forward Sanity activity logs to Datadog. See [Sanity webhook documentation][4] for more details.

1. Select an existing API key or create a new one by clicking one of the buttons below: <!-- UI Component to be added by Datadog team -->
2. Log in to your [Sanity account][2] as an Administrator. You are automatically redirected to the [manage page][3].
3. Select your project.
4. In the navigation panel, click **API**.
5. Click **Create Webhook**.
6. Add the name and webhook URL generated in step 1.
7. Select Dataset as `* (all datasets)`.
8. Under the **Trigger on** section, select the types of Document events you want to send to Datadog.
9. Under the **Projection** section, paste the below JSON:
    ```         
      { 
        "documentId": _id, 
        "documentType": _type, 
        "projectId": sanity::projectId(),
        "datasetName": sanity::dataset(),
        "action": "document." + delta::operation(),
        "beforeValues": before(),
        "afterValues": after(),
        "timestamp": now()
      }
    ```
    **Note**: It is recommended to _**uncheck**_ the **Trigger webhook when drafts are modified** checkbox in the Drafts section.
10. Ensure **POST** is selected under **HTTP method** in the **Advanced settings section**.
11. Click **Save**.

**Note**: These steps enable collection of document changes along with task and comment activity logs.

## Data Collected

### Logs

The Sanity integration collects and forwards Sanity activity logs to Datadog.

### Metrics

The Sanity integration does not include any metrics.

### Events

The Sanity integration does not include any events.

## Support

For further assistance, contact [Datadog Support][5].

[1]: https://www.sanity.io/
[2]: https://www.sanity.io/login
[3]: https://www.sanity.io/manage
[4]: https://www.sanity.io/docs/webhooks#
[5]: https://docs.datadoghq.com/help/

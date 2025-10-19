# Sanity

## Overview

[Sanity][1] is a headless content management system (CMS) designed for building flexible, real-time websites and applications. It enables developers and content teams to efficiently manage structured content across multiple platforms.

Integrate Sanity with Datadog to gain insights into content and project-related activity logs through the Sanity API and GROQ-powered Webhook. Pre-built dashboard visualizations provide immediate insights into Sanity activity logs.

**Minimum Agent version:** 7.61.0

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

### Retrieve the Datadog Webhook URL

1. Select an existing API key or create a new one by clicking one of the buttons below: <!-- UI Component to be added by Datadog team -->

**Note**: To set up the webhook, please follow the instructions provided in the Manual Webhook Configuration. Alternatively, you can use the Share Webhook Configurations option to apply a pre-configured setup.

### Manual Webhook Configuration

1. Log in to your [Sanity account][2] as an Administrator. You are automatically redirected to the [manage page][3].
2. Select your project.
3. In the navigation panel, click **API**.
4. Click **Create Webhook**.
5. Add the name and use the Datadog webhook URL.
6. Select Dataset as `* (all datasets)`.
7. Under the **Trigger on** section, select the types of Document events you want to send to Datadog.
8. Under the **Projection** section, paste the below JSON:
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
9. Ensure **POST** is selected under **HTTP method** in the **Advanced settings section**.
10. Click **Save**.

### Share Webhook Configuration

**Note**: These are alternative steps for **Manual Webhook Configuration**. Follow only one set of instructions.
1. Log in to your [Sanity account][2] as an Administrator.
2. To configure the webhook automatically, please follow the [Sanity webhook configuration][6].
3. Update the existing URL with the Datadog webhook URL.
4. Click **Apply webhook**.
5. In the configuration dialog, set the following parameters:
    - **Organization**: Select the organization from the dropdown list.
    - **Project**: Select the relevant project from the dropdown list.
    - **Dataset**: Select `* (all datasets)`.
6. Click **Create webhook**.

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
[6]: https://www.sanity.io/manage/webhooks/share?name=sanity-datadog&description=&url=https%3A%2F%2Fhttp-intake.logs.datadoghq.com%2Fapi%2Fv2%2Flogs%3Fdd-api-key%3D%3CYourDatadogAPIKey%3E%26ddsource%3Dsanity%26service%3Dactivity-logs&on=create&on=update&on=delete&filter=&projection=%7B%0A%20%20%20%20%22documentId%22%3A%20_id%2C%20%0A%20%20%20%20%22documentType%22%3A%20_type%2C%20%0A%20%20%20%20%22projectId%22%3A%20sanity%3A%3AprojectId()%2C%0A%20%20%20%20%22datasetName%22%3A%20sanity%3A%3Adataset()%2C%0A%20%20%20%20%22action%22%3A%20%22document.%22%20%2B%20delta%3A%3Aoperation()%2C%0A%20%20%20%20%22beforeValues%22%3A%20before()%2C%0A%20%20%20%20%22afterValues%22%3A%20after()%2C%0A%20%20%20%20%22timestamp%22%3A%20now()%0A%7D&httpMethod=POST&apiVersion=v2025-02-19&includeDrafts=&includeAllVersions=&headers=%7B%7D
## Overview

[Box][1] is a cloud-based file storage and collaboration platform that allows users to securely share, manage, and access files from anywhere.

This integration ingests the following logs:

- **Enterprise Events**: Enterprise events provide a detailed record of user activities (like uploads, downloads, sharing), administrative actions and shield events in an enterprise Box instance.

**Note**: [Box Shield][6] must be enabled on your Box Enterprise account to access security insights and threat detection data.

This integration gathers enterprise events and forwards them to Datadog for seamless analysis. Datadog leverages its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. With preconfigured dashboards, the integration offers clear visibility into activities within the Box platform. Additionally, it includes ready-to-use Cloud SIEM detection rules for enhanced monitoring and security.

## Setup

### Prerequisites

- Box Business or higher plan required.

### Generate API Credentials in Box

1. Log into Box and go to the [Developer Console][3]. Select **Create Platform App**.
2. Choose **Custom App**, enter required app info, then click **Next**, select **Server Authentication (with Client Credentials Grant)** as the authentication method, and then click **Create App**.
3. Go to the **Configuration** tab, select **App + Enterprise Access** under App Access Level, and check **Generate user access tokens** under Advanced Features.
4. In the **Authorization** tab, click **Review and Submit**, enter a brief app description, and click **Submit**.
5. Copy the **Enterprise ID** from the **General** tab, and the **Client ID** and **Client Secret** from the **Configuration** tab.
6. Navigate to the [Platform Apps Manager][4] in the Admin Console. Locate your app under **Server Authentication Apps**, click on **`...` (More)**, and select **Authorize App**. In the popup, click **Authorize** to confirm.

### Connect your Box Account to Datadog

1. Add your Enterprise ID, Client ID and Client Secret.
   | Parameters    | Description                                                 |
   | ------------- | ----------------------------------------------------------- |
   | Enterprise ID | The Enterprise ID of your organization in the Box platform. |
   | Client ID     | The Client ID of your organization in the Box platform.     |
   | Client Secret | The Client Secret of your organization in the Box platform. |

2. Click the Save button to save your settings.

**Note**: Monthly API call limits are outlined on the [Box Pricing Page][7]. If you need to purchase additional volume, please contact [Box Support][8].

## Data Collected

### Logs

The Box integration collects and forwards enterprise events to Datadog. For more details on the logs we collect with this integration, see the Box Enterprise Events API [Docs][5].

### Metrics

The Box integration does not include any metrics.

### Events

The Box integration does not include any events.

## Support

For any further assistance, contact [Datadog support][2].

[1]: https://www.box.com/
[2]: https://docs.datadoghq.com/help/
[3]: https://app.box.com/developers/console
[4]: https://app.box.com/master/platform-apps
[5]: https://developer.box.com/guides/events/enterprise-events/for-enterprise/#event-types
[6]: https://www.box.com/shield
[7]: https://www.box.com/pricing#:~:text=100-,API%20calls%20per%20month,-50%2C000*
[8]: https://support.box.com/

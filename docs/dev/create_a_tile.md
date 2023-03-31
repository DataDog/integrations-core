---
title: Create a Tile
type: documentation
description: Learn how to develop and publish an integration tile.
aliases:
- 'developers/marketplace/offering'
dependencies: "https://github.com/DataDog/integrations-core/blob/alai97/add-marketplace-documentation/docs/dev/create_a_tile.md"
further_reading:
- link: "https://partners.datadoghq.com/"
  tag: "Partner Network"
  text: "Datadog Partner Network"
- link: "https://www.datadoghq.com/blog/datadog-marketplace/"
  tag: "Blog"
  text: "Expand your monitoring reach with the Datadog Marketplace"
- link: "/developers/marketplace/"
  tag: "Documentation"
  text: "Learn about the Datadog Marketplace"
- link: "/developers/integrations/oauth_for_integrations"
  tag: "Documentation"
  text: "Learn about using OAuth for integrations"
---

## Overview

This page walks you through how to develop an offering on the Datadog Marketplace. If you have any questions, reach out to <a href="mailto:marketplace@datadoghq.com">marketplace@datadoghq.com</a>.

## Development process

To develop a Marketplace tile, follow these instructions:

1. [Choose a type of offering to list](#select-an-offering).
2. [Access the Marketplace repository and set up a directory](#set-up-a-directory-and-clone-the-marketplace-repository).
3. [Install and configure the Datadog Development Toolkit](#install-and-configure-the-datadog-development-toolkit).
4. [Populate the integration tile scaffolding](#populate-the-integration-tile-scaffolding).
5. [Complete the necessary integration asset files](#complete-the-necessary-integration-asset-files).
6. [Open a pull request](#open-a-pull-request).
7. [Review feedback and request approval to merge the pull request and release the integration tile](#review-process).
8. [Coordinate go-to-market opportunities with Partner Marketing](#coordinate-gtm-opportunities).

## Select an offering

A standard Marketplace integration tile appears with the following format:

{{< img src="developers/marketplace/marketplace-tile-example.png" alt="Example Marketplace tile" style="width:30%" >}}

Choose from the following offering types to create an integration tile that represents your listing on the [Datadog Marketplace][1]:

- A [Datadog Agent-based integration](#agent-based-integrations)
- A [REST API integration](#rest-api-integrations)
- A [Datadog App](#datadog-apps)
- A [SaaS license or subscription](#saas-license-or-professional-service-offerings)
- [Professional services](#saas-license-or-professional-service-offerings)

### Agent-based integrations

Agent-based integrations use the Datadog Agent to collect data, and are built around Agent checks. There are three types of checks:

- An [OpenMetrics check][2] is suitable for gathering telemetry data from existing applications that expose metrics using the OpenMetrics standard.
- A [Python check][3] is suitable for monitoring services or products that do not expose metrics in a standard format. Python checks can also be used to collect telemetry data from various APIs or command line tools.
- [DogStatsD][4] is suitable for applications that already emit telemetry using the StatsD protocol.

Agent integrations are bi-directional; they pull data from, and push data into Datadog. This differentiates them from informational tile-only listings on the Datadog Marketplace, such as a standalone SaaS license or a professional service offering, which are not bi-directional.

Integrations send the following types of data to Datadog:

- [Metrics][5]
- [Logs & Log Pipelines][6]
- [Events][7]
- [Service Checks][8]
- [Traces][9]
- [Incidents][10]
- [Security Events][11]

For more information about Datadog Agent-based integrations, see:

- [Introduction to Agent-based Integrations][12]
- [Creating your own solution][13]

### REST API integrations

Use an [API integration][14] to enrich and submit data from your backend, or pull data directly out of Datadog. API integrations work well in building a connector between Datadog and another SaaS platform. This method is ideal for Technology Partners that are SaaS based, and have an existing website for users to log into for authorization purposes.

Since API integrations do not use the Datadog Agent to collect data, you need to create an [informational tile-only listing](#saas-license-or-professional-service-offerings) once your development work is complete.

REST API integrations must be bi-directional, meaning that the integration should be able to pull data from and push data into Datadog.

REST API Integrations send the following types of data to Datadog:

- [Metrics][5]
- [Logs & Log Pipelines][6]
- [Events][7]
- [Service Checks][8]
- [Traces][9]
- [Incidents][10]
- [Security Events][11]

A Datadog API key is required to submit data to a Datadog API endpoint, and an application key is required to query data from Datadog. Instead of requesting these credentials directly from a user, Datadog recommends using [OAuth][15] to handle authorization and access for API-based integrations.

You can explore examples of existing API integrations in the `integrations-extras` repository such as [Vantage][24].

### Datadog Apps

[Datadog Apps][16] are custom dashboard widgets that are developed in the [Datadog Developer Platform][17]. Once your Datadog App is ready to publish, you need to create an [informational tile-only listing](#saas-license-or-professional-service-offerings) on the Integrations or Marketplace page.

### SaaS license or professional service offerings

To list a SaaS license or professional service offering in the Marketplace, you only need to create an informational tile-only listing.

## Set up a directory and clone the Marketplace repository

Once you've decided on an offering, set up a directory:

1. Request access to the [Marketplace repository][18] by following the instructions in the [Marketplace documentation][19].
2. Create a `dd` directory:
   {{< code-block lang="shell" >}}mkdir $HOME/dd{{< /code-block >}}

   The Datadog Development Toolkit command expects you to be working in the `$HOME/dd/` directory. This is not mandatory, but working in a different directory requires additional configuration steps.
3. Once you have been granted access to the Marketplace repository, create the `dd` directory and clone the `marketplace` repo:
   {{< code-block lang="shell" >}}git clone git@github.com:DataDog/marketplace.git{{< /code-block >}}
4. Create a feature branch to work in.

## Install and configure the Datadog development toolkit

The Agent Integration Developer Tool allows you to create scaffolding when you are developing an integration by generating a skeleton of your integration tile's assets and metadata. For instructions on installing the tool, see [Install the Datadog Agent Integration Developer Tool][25].

After you install the Developer tool, configure it for the `marketplace` repo:

Set `marketplace` as the default working repository:

{{< code-block lang="shell" >}}
ddev config set marketplace $HOME/dd/marketplace
ddev config set repo marketplace
{{< /code-block >}}

If you used a directory other than `$HOME/dd` to clone the marketplace directory, use the following command to set your working repository:

{{< code-block lang="shell" >}}
ddev config set marketplace <PATH/TO/MARKETPLACE>
ddev config set repo marketplace
{{< /code-block >}}

## Populate the integration tile scaffolding

Run the `ddev` command to generate a skeleton of the folders and files needed for your integration. The options you use with the command are different depending on what type of integration you are developing. For a full list of the files created by the `ddev` command, see [Integrations assets][22].

### Create an informational tile only listing

For Datadog Apps, Datadog REST API integrations, professional services, and standalone SaaS licenses, use the Datadog Development Toolkit to create scaffolding for an informational tile-only listing.

To create the informational tile-only listing's scaffolding:

1. Make sure you're inside the `marketplace` directory:
   {{< code-block lang="shell" >}}cd $HOME/dd/marketplace{{< /code-block >}}
2. Run the `ddev` command with the `-t tile` option:
   {{< code-block lang="shell" >}}ddev create -t tile "<Offering Name>"{{< /code-block >}}

### Create a full Agent-based integration

To generate the scaffolding for an Agent-based integration:
1. Make sure you're inside the `marketplace` directory:
   {{< code-block lang="shell" >}}cd $HOME/dd/marketplace{{< /code-block >}}
2. Run the `ddev` command:
   {{< code-block lang="shell" >}}ddev create "<Offering Name>"{{< /code-block >}}

## Complete the necessary integration asset files

Make sure that the following required assets for your integration are complete:

{{% integration-assets %}}

### README

Once you have created a `README.md` file, add the following sections as H2s (`##`) and fill out the content that is displayed in the Marketplace tile:

| Header Name | Header |
|-------------|--------|
| Overview | Write a description under an `## Overview` header that describes the value your offering provides to users and benefits to purchasing and installing the integration in the Datadog Marketplace (for example, out-of-the-box dashboards, replays of user sessions, logs, alerts, and more). <br><br>This information is displayed in the **Overview** tab on the integration tile. |
| Setup | Include all the steps to setting up your Marketplace integration that includes information divided into H3 headings (`###`). Standard topics include:<br><br>- Installing the integration using the in-app integration tile. <br>- Configuring the integration with the appropriate roles and permissions in your Datadog organization.<br>- Accessing out-of-the-box Datadog features that users who purchased and installed the integration can access (such as metrics, events, monitors, logs, dashboards, and more).|
| Uninstallation | Include all the steps to uninstalling your Marketplace integration. This information is displayed in the **Configure** tab on the integration tile.|
| Data Collected  | Specify the types of data collected by your Marketplace integration that includes information about out-of-the-box metrics, events, or service checks. <br><br>You can include additional types of data collected such as logs, monitors, dashboards, and more. If your Marketplace integration does not provide any of these, you do not need to add a Data Collected section. |
| Support | Provide contact information that includes an email to your Support team, a phone number to your company, a link to your company's documentation or blog post, and more help information in a bulleted list format. |

### Media Carousel

A media carousel of images and a video is included in your integration tile.

Technology Partners can add a video to an integration tile. Do not upload the video in your pull request. Instead, send a copy or a download link of your video to <a href="mailto:marketplace@datadoghq.com">marketplace@datadoghq.com</a>. The Marketplace team replies with a `vimeo_link` which you can add in the `manifest.json` file to include the video in the media carousel.

The video must meet the following requirements:

| Video Requirements | Description                                                                           |
|--------------------|---------------------------------------------------------------------------------------|
| Type               | MP4 H.264                                                                             |
| Size               | The maximum video size is 1GB.                                                        |
| Dimensions         | The aspect ratio must be 16:9 exactly and the resolution must be 1920x1080 or higher. |
| Name               | The video file name must be `partnerName-appName.mp4`.                                |
| Video Length       | The maximum video length is 60 seconds.                                               |
| Description        | The maximum number of characters allowed is 300.                                      |

Technology Partners can add up to eight images (seven if you are including a video) in an integration tile's media carousel.

The images must meet the following requirements:

| Image Requirements | Description                                                                                                                                       |
|--------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| Type               | `.jpg` or `.png`.                                                                                                                                 |
| Size               | The average is around 500KB. The maximum image size is 1MB.                                                                                       |
| Dimensions         | The aspect ratio must be 16:9 exactly and fit these specifications:<br><br>- Width: 1440px<br>- Minimum height: 810px<br>- Maximum height: 2560px |
| Name               | Use letters, numbers, underscores, and hyphens. Do not use spaces.                                                                           |
| Color Mode         | RGB                                                                                                                                               |
| Color Profile      | sRGB                                                                                                                                              |
| Description        | The maximum number of characters allowed is 300.                                                                                                  |

Follow this template to define the `media` object in the media carousel which includes an image, a video thumbnail, and a video:

{{< code-block lang="json" filename="manifest.json" collapsible="true" >}}
"media": [
      {
        "media_type": "image",
        "caption": "A Datadog Marketplace Integration OOTB Dashboard",
        "image_url": "images/integration_name_image_name.png"
      },
      {
        "media_type": "video",
        "caption": "A Datadog Marketplace Integration Overview Video",
        "image_url": "images/integration_name_video_thumbnail.png",
        "vimeo_id": 123456789
      },
    ],
{{< /code-block >}}

For more information, see [Integrations Assets Reference][22].

## Open a pull request

Push up your feature branch and open a pull request that contains your integration tile's asset files (including images) in the [`marketplace` repository][18]. The Marketplace repository does not allow forks. For instructions on creating a clone of the repo, see the [Set up section](#set-up-a-directory-and-clone-the-marketplace-repository). After you've created your pull request, automatic checks run in Azure DevOps pipelines to verify that your pull request is in good shape and contains all the required content to be updated.

To request access to the Azure DevOps pipeline, leave a comment in the pull request requesting access.

## Review process

Once your pull request passes all the checks, reviewers from the `Datadog/agent-integrations`, `Datadog/marketplace-review`, and `Datadog/documentation` teams provide suggestions and feedback on best practices.

Once you have addressed the feedback and re-requested reviews, these reviewers approve your pull request. Contact the Marketplace team if you would like to preview the integration tile in your sandbox account. This allows you to validate and preview additional changes in the integration tile on the Datadog Marketplace before your pull request is merged.

## Coordinate GTM opportunities

Once a Marketplace tile is live, Technology Partners can meet with Datadog's Partner Marketing team to coordinate a joint go-to-market (GTM) strategy, which includes the following:

- A Datadog quote for partner press releases
- A blog post on the [Datadog Monitor][23]
- Amplification of social media posts

## Further Reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: https://app.datadoghq.com/marketplace/
[2]: https://docs.datadoghq.com/developers/custom_checks/prometheus/
[3]: https://docs.datadoghq.com/developers/integrations/new_check_howto/?tab=configurationtemplate#write-the-check
[4]: https://docs.datadoghq.com/developers/dogstatsd/
[5]: https://docs.datadoghq.com/api/latest/metrics/
[6]: https://docs.datadoghq.com/logs/faq/partner_log_integration/
[7]: https://docs.datadoghq.com/api/latest/events/
[8]: https://docs.datadoghq.com/api/latest/service-checks/
[9]: https://docs.datadoghq.com/tracing/guide/send_traces_to_agent_by_api/
[10]: https://docs.datadoghq.com/api/latest/incidents/
[11]: https://docs.datadoghq.com/api/latest/security-monitoring/
[12]: https://docs.datadoghq.com/developers/integrations/
[13]: https://docs.datadoghq.com/developers/#creating-your-own-solution
[14]: https://docs.datadoghq.com/api/latest/
[15]: https://docs.datadoghq.com/developers/integrations/oauth_for_integrations/
[16]: https://docs.datadoghq.com/developers/datadog_apps/
[17]: https://app.datadoghq.com/apps/
[18]: https://github.com/Datadog/marketplace
[19]: https://docs.datadoghq.com/developers/marketplace/#request-access-to-marketplace
[20]: https://www.python.org/downloads/
[21]: https://pypi.org/project/datadog-checks-dev/
[22]: https://docs.datadoghq.com/developers/integrations/check_references/#manifest-file
[23]: https://datadoghq.com/blog/
[24]: https://github.com/DataDog/integrations-extras/tree/master/vantage
[25]: https://docs.datadoghq.com/developers/integrations/python

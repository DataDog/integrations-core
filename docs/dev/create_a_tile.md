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
- link: "/developers/integrations/marketplace_offering/"
  tag: "Documentation"
  text: "Learn how to build a Marketplace offering"
- link: "/developers/integrations/oauth_for_integrations"
  tag: "Documentation"
  text: "Learn about using OAuth for integrations"
---

## Overview

This page walks you through how to develop an offering on the Datadog Marketplace. If you have any questions, reach out to <a href="mailto:marketplace@datadoghq.com">marketplace@datadoghq.com</a>.

{{% tab "Marketplace Offerings" %}}
## Set up a directory and clone the Marketplace repository

Set up a directory:

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

### Create an informational tile only listing

For API integrations, Datadog Apps, professional services, or standalone SaaS licenses that will be offered for an additional cost on the Datadog Marketplace, use the Datadog Development Toolkit to create scaffolding for an informational tile-only listing.

To create the informational tile-only listing's scaffolding:

1. Make sure you're inside the `marketplace` directory:
   {{< code-block lang="shell" >}}cd $HOME/dd/marketplace{{< /code-block >}}
2. Run the `ddev` command with the `-t tile` option:
   {{< code-block lang="shell" >}}ddev create -t tile "<Offering Name>"{{< /code-block >}}

{{% /tab %}}

{{% tab "Out of the box Offerings" %}}

## Set up a directory and fork the `integrations-extras` repository


1. Create a `dd` directory:

   {{< code-block lang="shell" >}}mkdir $HOME/dd{{< /code-block >}}
   
   The Datadog Development Toolkit expects you to be working in the `$HOME/dd/` directory. This is not mandatory, but working in a different directory requires additional configuration steps.

2. Clone the `integrations-extras` repository:

   {{< code-block lang="shell" >}}git clone git@github.com:DataDog/integrations-extras.git{{< /code-block >}}

## Install and configure the Datadog development toolkit

The Agent Integration Developer Tool allows you to create scaffolding when you are developing an integration by generating a skeleton of your integration tile's assets and metadata. For instructions on installing the tool, see [Install the Datadog Agent Integration Developer Tool][23].

After you install the Developer tool, configure it for the `integrations-extras` repo:

Set `integrations-extras` as the default working repository:

{{< code-block lang="shell" >}}
ddev config set extras $HOME/dd/integrations-extras
ddev config set repo extras
{{< /code-block >}}

If you used a directory other than `$HOME/dd` to clone the integrations-extras directory, use the following command to set your working repository:

{{< code-block lang="shell" >}}
ddev config set extras <PATH/TO/INTEGRATIONS_EXTRAS>
ddev config set repo extras
{{< /code-block >}}

## Populate the integration tile scaffolding

For Datadog API integrations and Datadog Apps that will be available out-of-the-box on the [Integrations page], use the Datadog Development Toolkit to create scaffolding for an informational tile-only listing.

1. Make sure you're inside the `integrations-extras` directory:
   {{< code-block lang="shell" >}}cd $HOME/dd/integrations-extras{{< /code-block >}}
2. Run the `ddev` command with the `-t tile` option
   {{< code-block lang="shell" >}}ddev create -t tile "<Offering Name>"{{< /code-block >}}


{{% /tab %}}

## Complete the necessary integration asset files

Make sure that the following required assets for your integration are complete:

{{% integration-assets %}}

### README

Once you have created a `README.md` file, add the following sections as H2s (`##`) and fill out the content that is displayed in the Marketplace tile:

| Header Name | Header |
|-------------|--------|
| Overview | Write a description under an `## Overview` header that describes the value and benefits your offering provides to users, for example, out-of-the-box dashboards, replays of user sessions, logs, alerts, and more). <br><br>This information is displayed in the **Overview** tab on the integration tile. |
| Setup | Include all the steps to setting up your offering that includes information divided into H3 headings (`###`). Standard topics include:<br><br>- Installing the integration using the in-app integration tile. <br>- Configuring the integration with the appropriate roles and permissions in your Datadog organization.<br>- Accessing out-of-the-box Datadog features that users who purchased and installed the integration can access (such as metrics, events, monitors, logs, dashboards, and more).|
| Uninstallation | Include all the steps for uninstalling your offering. This information is displayed in the **Configure** tab on the integration tile.|
| Data Collected  | Specify the types of data collected by your integration (if applicable) including information about out-of-the-box metrics, events, or service checks. <br><br>You can include additional types of data collected such as logs, monitors, dashboards, and more. If your offering does not provide any of this data, you do not need to add a Data Collected section. |
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

Before you open a pull request, run the following command to catch any problems with your integration:
```
ddev validate all <INTEGRATION_NAME>
```


## Open a pull request

Push up your feature branch and open a pull request that contains your integration tile's asset files (including images) in the [`marketplace`][18] or [`integrations-extras`][number] repository. The Marketplace repository does not allow forks. For instructions on creating a clone of the repo, see the [Set up section](#set-up-a-directory-and-clone-the-marketplace-repository). After you've created your pull request, automatic checks will run to verify that your pull request is in good shape and contains all the required content to be updated.
`Please note we have stopped using Azure DevOps`

## Review process

Once your pull request passes all checks, reviewers from the `Datadog/agent-integrations`, `Datadog/marketplace-review`, and `Datadog/documentation` teams provide suggestions and feedback on best practices.

Once you have addressed the feedback and re-requested reviews, these reviewers approve your pull request. Contact the Marketplace team if you would like to preview the tile in your sandbox account. This allows you to validate and preview additional changes on the tile before your pull request is merged.

### How to resolve common validation errors 

Out-of-the-box integrations wtihin the integrations-extras repository can run into validation errors when the forked reposiotry is out of date with the origin. Follow the steps below to resolve the validation errors by rebasing. 

Updating the forked repository via the Web App

1. Go to the github.com
2. Go to your repositories
3. Select your forked repo of integrations-extras
4. Go to "sync fork"  in the github web--ui 
5. Click "update branch" 

To rebase and push changes:

git checkout <your working branch>

git rebase master

   If there are any merge conflicts, you'd resolve them here

git push origin <working branch> -f

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
[19]: https://docs.datadoghq.com/developers/integrations/marketplace_offering/#request-access-to-marketplace
[20]: https://www.python.org/downloads/
[21]: https://pypi.org/project/datadog-checks-dev/
[22]: https://docs.datadoghq.com/developers/integrations/check_references/#manifest-file
[23]: https://datadoghq.com/blog/
[24]: https://github.com/DataDog/integrations-extras/tree/master/vantage
[25]: https://docs.datadoghq.com/developers/integrations/python

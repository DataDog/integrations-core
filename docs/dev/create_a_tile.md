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

This page walks you through how to create the tile that represents your offering. This tile will appear on the Datadog Integrations page or on the Datadog Marketplace, and you can see an example of a tile below: 

{{< img src="developers/marketplace/marketplace-tile-example.png" alt="Example Marketplace tile" style="width:30%" >}}

The tile serves as an informative point of entry where customers can learn more about your offering, learn how to set it up, as well as install or purchase your offering to unlock out-of-the-box dashboards and other assets. 

For **any offerings that do not use the Datadog Agent**, including API-based integrations, professional services listings, and software licenses, you will only need to create a tile, and submit the tile-related files, in order to publish your offering. This is called a **tile-only-listing**. Only a tile is needed in this scenario because Datadog does not host any of the code associated with API-based integrations, and the other types of offerings we support do not require any code. 

For **Agent-based integrations**, however, you will need to create a tile, and _additionally_ submit all of your integration-related code (as well as your tile-related files) in one pull request, as described in [Create an Agent-based integration][27].


**Select an option below to get started and create a tile on either the Marketplace or Integrations page:** 

{{< tabs >}}

{{% tab "Build a tile on the Integrations page" %}}

## Set up a directory and fork the `integrations-extras` repository


1. Create a `dd` directory:

   {{< code-block lang="shell" >}}mkdir $HOME/dd{{< /code-block >}}
   
   The Datadog Development Toolkit expects you to be working in the `$HOME/dd/` directory. This is not mandatory, but working in a different directory requires additional configuration steps.

2. Clone the `integrations-extras` repository:

   {{< code-block lang="shell" >}}git clone git@github.com:DataDog/integrations-extras.git{{< /code-block >}}

## Install and configure the Datadog development toolkit

The Agent Integration Developer Tool allows you to create scaffolding when you are developing an integration by generating a skeleton of your integration tile's assets and metadata. For instructions on installing the tool, see [Install the Datadog Agent Integration Developer Tool][101].

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

For Datadog API integrations that will be available out-of-the-box on the [Integrations page][102], use the Datadog Development Toolkit to create scaffolding for a tile-only listing.

1. Make sure you're inside the `integrations-extras` directory:
   {{< code-block lang="shell" >}}cd $HOME/dd/integrations-extras{{< /code-block >}}
2. Run the `ddev` command with the `-t tile` option
   {{< code-block lang="shell" >}}ddev create -t tile "<Offering Name>"{{< /code-block >}}

[101]: https://docs.datadoghq.com/developers/integrations/python
[102]: https://github.com/Datadog/integrations-extras

{{% /tab %}}

{{% tab "Build a tile on the Marketplace" %}}

## Set up a directory and clone the Marketplace repository

Set up a directory:

1. Request access to the [Marketplace repository][101] by following the instructions in the [Marketplace documentation][102].

2. Create a `dd` directory:
   
   {{< code-block lang="shell" >}}mkdir $HOME/dd{{< /code-block >}}

   The Datadog Development Toolkit command expects you to be working in the `$HOME/dd/` directory. This is not mandatory, but working in a different directory requires additional configuration steps.

3. Once you have been granted access to the Marketplace repository, create the `dd` directory and clone the `marketplace` repo:
   
   {{< code-block lang="shell" >}}git clone git@github.com:DataDog/marketplace.git{{< /code-block >}}

4. Create a feature branch to work in.


## Install and configure the Datadog development toolkit

The Agent Integration Developer Tool allows you to create scaffolding when you are developing an integration by generating a skeleton of your integration tile's assets and metadata. For instructions on installing the tool, see [Install the Datadog Agent Integration Developer Tool][103].

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

Use the Datadog Development Toolkit to create scaffolding for a tile-only listing.

To create the tile-only listing's scaffolding:

1. Make sure you're inside the `marketplace` directory:
   {{< code-block lang="shell" >}}cd $HOME/dd/marketplace{{< /code-block >}}
2. Run the `ddev` command with the `-t tile` option:
   {{< code-block lang="shell" >}}ddev create -t tile "<Offering Name>"{{< /code-block >}}

[101]: https://github.com/Datadog/marketplace
[102]: https://docs.datadoghq.com/developers/integrations/marketplace_offering
[103]: https://docs.datadoghq.com/developers/integrations/python

{{% /tab %}}
{{< /tabs >}}

## Complete the necessary integration asset files

Make sure that the following required assets for your integration are complete:

{{% integration-assets %}}

### README

Once you have created a `README.md` file, add the following sections as H2s (`##`) and fill out the content accordingly:

| Header Name | Header |
|-------------|--------|
| Overview | Write a description under an `## Overview` header that describes the value and benefits your offering provides to users, for example, out-of-the-box dashboards, replays of user sessions, logs, alerts, and more). <br><br>This information is displayed in the **Overview** tab on the tile. |
| Setup | Include all the steps required to set up your offering that includes information divided into H3 headings (`###`). Standard topics include:<br><br>- Installing the integration using the in-app integration tile. <br>- Configuring the integration with the appropriate roles and permissions in your Datadog organization.<br>- Accessing out-of-the-box Datadog features that users who purchased and installed the integration can access (such as metrics, events, monitors, logs, dashboards, and more).|
| Uninstallation | Include all the steps for uninstalling your offering. This information is displayed in the **Configure** tab on the tile.|
| Data Collected  | Specify the types of data collected by your integration (if applicable), including events, service checks, logs, etc. Metrics added to the `metadata.csv` file will automatically appear in this tab.  <br><br> If your offering does not provide any of this data, you do not need to add a Data Collected section. |
| Support | Provide contact information that includes an email to your Support team, a link to your company's documentation or blog post, and more help information in a bulleted list format. |

### Media carousel

A media carousel of images and a video is displayed on each tile, allowing users to better understand the functionality and value of your offering through visual aids.

To add a video to your tile, send a copy or a download link of your video to <a href="mailto:marketplace@datadoghq.com">marketplace@datadoghq.com</a>. The Marketplace team uploads the video and provides a `vimeo_link` that should be added to the `manifest.json` file.

The video must meet the following requirements:

| Video Requirements | Description                                                                           |
|--------------------|---------------------------------------------------------------------------------------|
| Type               | MP4 H.264                                                                             |
| Size               | The maximum video size is 1GB.                                                        |
| Dimensions         | The aspect ratio must be 16:9 exactly and the resolution must be 1920x1080 or higher. |
| Name               | The video file name must be `partnerName-appName.mp4`.                                |
| Video Length       | The maximum video length is 60 seconds.                                               |
| Description        | The maximum number of characters allowed is 300.                                      |

Technology Partners can add up to eight images (seven if you are including a video) in a tile's media carousel.

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

Follow this template to define the `media` object in the `manifest.json` file which includes an image, a video thumbnail, and a video:

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

Before you open a pull request, run the following command to catch any problems with your integration:
```
ddev validate all <INTEGRATION_NAME>
```

Next, complete the following steps:

1. Commit all changes to your feature branch.
2. Push your changes to the remote repository. 
3. Open a pull request that contains your integration tile's asset files (including images) in the [`marketplace`][18] or [`integrations-extras`][26] repository. 
4. After you've created your pull request, automatic checks will run to verify that your pull request is in good shape and contains all the required content to be updated.

## Review process

Once your pull request passes all checks, reviewers from the `Datadog/agent-integrations`, `Datadog/marketplace-review`, and `Datadog/documentation` teams provide suggestions and feedback on best practices.

Once you have addressed the feedback and re-requested reviews, these reviewers approve your pull request. Contact the Marketplace team if you would like to preview the tile in your sandbox account. This allows you to validate and preview your tile before your tile is live to all customers.

### How to resolve common validation errors 

Out-of-the-box integrations in the `integrations-extras` repository can run into validation errors when the forked repository is out of date with the origin. Follow the steps below to resolve the validation errors by rebasing. 

Updating the forked repository via the Web App

1. Go to github.com
2. Go to your repositories
3. Select your forked repo of integrations-extras
4. Go to "sync fork" in the top right corner 
5. Click "update branch" 

To rebase and push changes:

1. `git checkout <your working branch>`

2. `git rebase master`

-  If there are any merge conflicts, you'd resolve them here

3. `git push origin <working branch> -f`


### Go-to-Market (GTM) opportunities

Datadog offers GTM support for Marketplace listings only. To learn more about the Datadog Marketplace, see [Create a Marketplace Offering][NEEDS LINK].

## Further reading

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
[26]: https://github.com/Datadog/integrations-extras
[27]: https://docs.datadoghq.com/developers/integrations/agent_integration/

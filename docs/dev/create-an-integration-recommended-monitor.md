---
title: Create an Integration Recommended Monitor
kind: documentation
further_reading:
- link: "/monitors/configuration/"
  tag: "Documentation"
  text: "Configure Monitors"
---

## Overview

[Datadog Monitors][1] track key metrics, so you can efficiently monitor your infrastructure and integrations. Datadog provides a set of out-of-the-box monitors for many features and integrations. View these monitors in your [Monitors Template list][2].

Create an out-of-the-box monitor to help users find value in your Datadog integration. This guide provides steps for creating an integration recommended monitor and best practices to follow during the creation process.

To create a Datadog integration, see [Create a New Integration][3].

## Steps to create a recommended monitor
### Build a monitor JSON Schema

1. Navigate to **[Monitors > New Monitor][4]** and create a new monitor.

2. Follow the [best practices](#configuration-best-practices) listed in this guide to configure your monitor.
 
3. Click **Export Monitor**.

4. Check **Select to export as a recommended monitor**.
    {{< img src="developers/integrations/monitor_json.png" alt="Monitor JSON modal to export as recommended monitor" style="width:100%;" >}}

5. Click **Copy** to use the JSON schema of your configured monitor.

6. Save the copied schema to a JSON file and name it according to your monitor title. For example, `your_integration_name_alert.json`.

7. In the monitor JSON file, fill out the Title, Description, and Tags. For more information, see [Configuration best practices](#configuration-best-practices). 

### Open a pull request

1. Save the monitor JSON file to your integration's `assets/monitors` folder.  Add the asset to your `manifest.json` file. See [Integrations Assets Reference][5] for more information about your integration's file structure and manifest file.

2. Open a pull request (PR) to add your recommended monitor JSON file and updated manifest file to the corresponding integration folder in the [`integrations-extras` GitHub repository][6]. 

3. After it's approved, Datadog merges the PR and your integration recommended monitor is pushed to production.

## Verify your monitor in production

To see the out-of-the-box monitor, the relevant integration tile must be `Installed` in Datadog. 

Find your monitor in the [Monitors Template list][2]. Ensure logos render correctly on the Monitors Template lists page.

## Configuration best practices

In addition to the monitor definition, the Title, Description, and Tags fields are required for recommended monitors. For more information, see the documentation on [configuring a monitor][7].

|      | Description    | Examples |
| ---  | ----------- | ----------- |
|Title | Allows users to quickly understand the underlying failure mode the alert is covering.| - New flaky tests<br> - High CPU usage on hosts<br> - New Error Tracking issues</br> - Too many opened connections on databases|
|Description | Provides extra context around the failure mode and also about the impact this mode can have on the system. It should be concise and allow users to understand at a glance whether it is relevant or not for them to create a monitor out of it.| **Title**: Too many opened connections on databases<br> **Description**: Get notified whenever the number of connections to the database is too high. When too many connections are opened, new clients might not be able to open new connections and thus to execute the queries serving end-users.|
|Tags | Set to "integration:<app_id>".| See other available monitor tags [here][8].|

Below is an example of a well-defined monitor:

{{< img src="developers/integrations/example_recommended_monitor_config.png" alt="An example of a Recommended Monitor configuration" width="100%">}}

## Further reading

{{< partial name="whats-next/whats-next.html" >}}

[1]: /monitors
[2]: https://app.datadoghq.com/monitors/recommended
[3]: /developers/integrations/new_check_howto/?tab=configurationtemplate
[4]: https://app.datadoghq.com/monitors/create
[5]: /developers/integrations/check_references/#manifest-file
[6]: https://github.com/DataDog/integrations-extras
[7]: /monitors/configuration/
[8]: /monitors/manage/#monitor-tags

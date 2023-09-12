---
title: Create an Integration Recommended Monitor
kind: documentation
---

## Overview

[Datadog Monitors][1] enable you to efficiently monitor your infrastructure and integrations by tracking key metrics. Datadog provides a set of out-of-the-box monitors for many features and integrations. You can access these by viewing your [Monitors Template list][4].

If you have [created a Datadog integration][2], you may wish to create an out-of-the-box monitor to help your integration's users more quickly find value in your integration. This guide provides steps for creating an integration recommended monitor and best practices to follow during the creation process.

To create a Datadog integration, see [Create a New Integration][2].


## Create an integration recommended monitor
### Create a new monitor

In Datadog, [create a new monitor][4]. 

Follow the best practices in this guide when defining your monitor.

### Export your monitor

Select the checkbox to export the monitor as a recommended monitor.
Export your monitor to JSON using the export button.
Name the file according to your monitor title: for example, `your_integration_name_alert.json`.

Within the monitor JSON file, fill out the Title, Description, and Tags. See [follow alerting best practices][#follow-alerting-best-practices] for more info on how to best fill out these fields. 

Save this file to your integration's `assets/monitors` folder.  Add the asset to your `manifest.json` file. See [Integrations Assets Reference][3] for more information about your integration's file structure and manifest file.

### Open a pull request

Open a pull request (PR) to add your recommended monitor JSON file and updated manifest file to the corresponding integration folder in the [`integrations-extras` GitHub repository][5]. Datadog reviews all `integration-extras` PRs. Once approved, Datadog merges the PR and your integration recommended monitor is pushed to production.

### Verify your monitor in production

First, ensure the relevant integration tile is `Installed` in Datadog. You must install an integration to see its associated out-of-the-box monitors.

Find your monitor in [Monitors Template list][4]. Ensure logos render correctly on the Monitors Template lists page.

## Follow alerting best practices

Below is an example of a well-defined monitors:

{{< img src="developers/create-an-integration-recommended-monitor/monitor-example.png" alt="An example of a Recommended Monitor" width="100%">}}

Refer to our [documentation on defining a monitor][6].

In addition to the monitor definition, the Title, Description, and Tags fields are required for recommended monitors. Below are best practices for these fields:
- **Title** is what users see when browsing the content in the Datadog platform, it should allow them to quickly understand the underlying failure mode the alert is covering. See examples below:
    - New flaky tests
    - High CPU usage on hosts
    - New Error Tracking issues
    - Too many opened connections on databases
- **Description** should be used to provide extra context around the failure mode and also about the impact this mode can have on the system. It should be concise and allow users to understand at a glance whether it is relevant or not for them to create a monitor out of it.
    - For example: “Too many opened connections on databases”: Get notified whenever the number of connections to the database is too high. When too many connections are opened, new clients might not be able to open new connections and thus to execute the queries serving end-users.
- **Tags** should be set to "integration:<app_id>". See other available tags [here][7].


[1]: /monitors
[2]: /developers/integrations/new_check_howto/?tab=configurationtemplate
[3]: /developers/integrations/check_references/#manifest-file
[4]: https://app.datadoghq.com/monitors/recommended
[5]: https://github.com/DataDog/integrations-extras
[6]: https://docs.datadoghq.com/monitors/configuration/
[7]: https://docs.datadoghq.com/monitors/manage/#monitor-tags
[8]: 

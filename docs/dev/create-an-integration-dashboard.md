---
title: Create an Integration Dashboard
kind: documentation
---

## Overview

[Datadog Dashboards][1] enable you to efficiently monitor your infrastructure and integrations by displaying and tracking key metrics. Datadog provides a set of out-of-the-box dashboards for many features and integrations. You can access these by viewing your [Dashboard List][12].

If you have [created a Datadog integration][2], you may wish to create an out-of-the-box dashboard to help your integration's users more quickly find value in your integration. This guide provides steps for creating an integration dashboard and best practices to follow during the creation process.

To create a Datadog integration, see [Create a New Integration][2].


## Create an integration dashboard
### Create a new dashboard

In Datadog, [create a new dashboard][12]. 

Follow the best practices in this guide when adding elements to your dashboard.

### Export your dashboard

Export your dashboard to JSON using the settings cog (upper right) and choosing **Export dashboard JSON**.
Name the file according to your dashboard title: for example, `you_integration_name_overview.json`.

Save this file to your integration's `assets/dashboards` folder.  Add the asset to your `manifest.json` file. See [Integrations Assets Reference][11] for more information about your integration's file structure and manifest file.

### Open a pull request

Open a pull request (PR) to add your dashboard JSON file and updated manifest file to the corresponding integration folder in the [`integrations-extras` GitHub repository][13]. Datadog reviews all `integration-extras` PRs. Once approved, Datadog merges the PR and your integration dashboard is pushed to production.

### Verify your dashboard in production

First, ensure the relevant integration tile is `Installed` in Datadog. You must install an integration to see its associated out-of-the-box dashboards.

Find your dashboard in [Dashboard Lists][12]. Ensure logos render correctly on the Dashboard Lists page and within the preset dashboard.

## Follow dashboard best practices

An integration dashboard should contain the following information:

{{< img src="developers/create-an-integration-dashboard/dashboard-example.png" alt="An example of a Dashboard" width="100%">}}

- An attention-grabbing **About** group with a banner image, concise copy, useful links, and good typography hierarchy
- A brief annotated **Overview** group with the most important statistics at the top
- Simple graph titles and title-case group names
- Symmetry in high density mode
- Well-formatted, concise notes
- Color coordination between related groups, notes within groups, and graphs within groups


### General guidelines

-  When creating a new dashboard, select the default dashboard type.

-  Put the integration name in your dashboard title. Some examples of a good dashboard title are `Scylla` or `Cilium Overview`. **Note**: Avoid using `-` (hyphens) in the dashboard title, as the dashboard URL is generated from the title.

-  Add a logo to the dashboard header. The integration logo automatically appears in the header if the icon exists and the `integration_id` matches the icon name.

-  Include an About group for the integration containing a brief description and helpful links. The About section should contain content, not data. Avoid making the About section full-width.

- Edit the About section and select the banner display option. You can then link to a banner image according to the following file location: `/static/images/integration_dashboard/your-image.png`.

- Include an Overview group containing a few of the most important metrics and place it at the top of the dashboard. The Overview group can contain data.

-  Check to see how your dashboard looks at 1280px wide and 2560px wide. This is how the dashboard appears on a smaller laptop and a larger monitor, respectively. The most common screen widths for dashboards are 1920, 1680, 1440, 2560, and 1280px. If your monitor is not large enough for high density mode, use the browser zoom controls to zoom out.

### Widgets and grouping

-  Research the metrics supported by the integration and consider grouping them in relevant categories. Important metrics that are key to the performance and the overview of the integration should be at the top.

-  Use Group widgets to title and group sections, rather than note widgets. Use partial width groups to display groups side-by-side. Most dashboards should display every widget within a group.

    {{< img src="developers/create-an-integration-dashboard/full-width-grouped-logs.png" alt="An example of Group widgets" width="100%">}}

-  Timeseries widgets should be at least four columns wide in order not to appear squashed on smaller displays.

-  Stream widgets should be at least six columns wide, or half the dashboard width, for readability. Place them at the end of a dashboard so they don't trap scrolling. It's useful to put stream widgets in a group by themselves so they can be collapsed. Add an event stream only if the service monitored by the dashboard is reporting events. Use `sources:service_name`.

-  Try using a mix of widget types and sizes. Explore visualizations and formatting options until you're confident your dashboard is as clear as it can be. Sometimes a whole dashboard of timeseries is okay, but other times variety can improve legibility. The most commonly used metric widgets are [timeseries][4], [query values][5], and [tables][6]. For more information on the available widget types, see the [list of supported dashboard widgets][7].

-  Try to make the left and right halves of your dashboard symmetrical in high density mode. Users with large monitors will see your dashboard in high density mode by default, so it's important that group relationships make sense, and that the dashboard looks good. You can adjust group heights to achieve this, and move groups between the left and right halves.

    {{< img src="developers/create-an-integration-dashboard/symmetrical-dashboard.png" alt="An example of a symmetrical dashboard" width="100%">}}

-  [Template variables][8] allow you to dynamically filter one or more widgets in a dashboard. Template variables must be universal and accessible by any user or account using the monitored service. Ensure all relevant graphs are listening to the relevant template variable filters.

    **Note**: Adding `*=scope` as a template variable is useful as users can access all of their own tags.

### Copy

-  Use concise graph titles that start with the most important information. Avoid common phrases such as "number of".

    | Concise title (good) | Verbose title (bad) |
    | - | - |
    | Events per node | Number of Kubernetes events per node |
    | Pending tasks: [$node_name] | Total number of pending tasks in [$node_name] |
    | Read/write operations | Number of read/write operations |
    | Connections to server - rate | Rate of connections to server |
    | Load | Memcached Load |

-  Avoid repeating the group title or integration name in every widget in a group, especially if the widgets are query values with a custom unit of the same name.

-  For the timeseries widget, always [alias formulas][9].

-  Group titles should be title case. Widget titles should be sentence case.

-  If you're showing a legend, make sure the aliases are easy to understand.

-  Graph titles should summarize the queried metric. Do not indicate the unit in the graph title because unit types are displayed automatically from metadata. An exception to this is if the calculation of the query represents a different type of unit.

### Visual style

-  Format notes to make them fit their use case. Try the presets "caption", "annotation", or "header", or pick your own combination of styles. Avoid using the smallest font size for notes that are long or including complex formatting, like bulleted lists or code blocks.

-  Use colors to highlight important relationships and to improve readability, not for style. If several groups are related, apply the same group header color to all of them. If you've applied a green header color to a group, try making its notes green as well. If two groups are related, but one is more important, try using the "vivid" color on the important group and the "light" color on the less important group. Don't be afraid to leave groups with white headers, and be careful not to overuse color. For example, don't make every group on a dashboard vivid blue. Also avoid using gray headers.

    {{< img src="developers/create-an-integration-dashboard/color-related-data.png" alt="An example of color-related data in a dashboard" width="100%">}}

-  Use legends when they make sense. Legends make it easy to read a graph without having to hover over each series or maximize the widget. Make sure you use timeseries aliases so the legend is easy to read. Automatic mode for legends is a great option that hides legends when space is tight and shows them when there's room.

    {{< img src="developers/create-an-integration-dashboard/well-named-legends.png" alt="An example of legends in a dashboard" width="100%">}}

-  If you want users to compare two graphs side-by-side, make sure their x-axes align. If one graph is showing a legend and the other isn't, the x-axes won't align. Make sure they both show a legend or both do not.

-  For timeseries, base the display type on the type of metric.

    | Types of metric | Display type |
    | - | - |
    | Volume (e.g. Number of connections) | `area` |
    | Counts (e.g. Number of errors) | `bars` |
    | Multiple groups or default | `lines` |


[1]: /dashboards/
[2]: /developers/integrations/new_check_howto/?tab=configurationtemplate
[3]: /dashboards/#new-dashboard
[4]: /dashboards/widgets/timeseries/
[5]: /dashboards/widgets/query_value/
[6]: /dashboards/widgets/table/
[7]: /dashboards/widgets/
[8]: /dashboards/template_variables/
[9]: /dashboards/widgets/timeseries/#metric-aliasing
[10]: /dashboards/#copy-import-or-export-dashboard-json
[11]: /developers/integrations/check_references/#manifest-file
[12]: https://app.datadoghq.com/dashboard/lists
[13]: https://github.com/DataDog/integrations-extras

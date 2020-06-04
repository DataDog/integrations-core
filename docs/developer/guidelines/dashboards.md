# Dashboards

-----

Datadog dashboards enable you to efficiently monitor your infrastructure and integrations
 by displaying and tracking key metrics.
 
## Integration Preset Dashboards

If you would like to create a default dashboard for an integration, follow the guidelines in the [Best Practices](./dashboards.md#best-practices) section.

### Exporting a dashboard payload
When you've created a dashboard in the Datadog UI, you can export the dashboard payload to be included in its integration's assets directory.

Ensure that you have set an `API_KEY` and `APP_KEY` for the org that contains the new dashboard in the ddev [configuration](https://datadoghq.dev/integrations-core/ddev/cli/#set).

Run the following command to [export the dashboard](../ddev/cli.md#export):

```cli
ddev meta dash export <URL_OF_DASHBOARD> <INTEGRATION>
```

!!! tip
    If the dashboard is for a contributor-maintained integration in the `integration-extras` repo, run the command with the `--extras` or `-e` flag.

The command will add the dashboard definition to the `manifest.json` file of the integration. 
The dashboard JSON payload will be available in `/assets/dashboards/<DASHBOARD_TITLE>.json`.

Commit the changes and create a pull request.

### Verify the Preset Dashboard

Once your PR is merged and synced on production, you can find your dashboard in the Dashboard List page.

!!! tip
    Make sure the integration tile is `Installed` in order to see the preset dashboard in the list.

Ensure logos render correctly on the Dashboard List page and within the preset dashboard. 

## Best Practices

![Mongo dashboard](https://raw.githubusercontent.com/DataDog/integrations-core/master/docs/developer/assets/images/mongo_dashboard.png)

1. When creating a new dashboard, select the Screenboard type.

    !!! information
        Integration preset (or out of the box) dashboards are typically screenboards because they allow images, widgets, and labels. 
        Learn more about Datadog dashboards and see the differences between [screenboards and timeboards](https://docs.datadoghq.com/dashboards/#screenboard-vs-timeboard). 

1. Dashboard titles should contain the integration name. Some examples of a good dashboard title is `Syclla` or `Cilium Overview`.
- Avoid using `-` in the dashboard title as the dashboard URL is generated from the title.

1. Research the metrics supported by the integration and consider grouping them in relevant categories. 
Important metrics that are key to the performance and overview of the integration should be at the top.

1. Ensure good design by keeping labels and widgets aligned with consistent spacing and reasonable size. 

!!! tip
    Use [`TV Mode`](https://docs.datadoghq.com/dashboards/screenboards/#tv-mode) to ensure that the whole dashboard fit on your horizontal screen.

### Logos

Integration logos should be placed at the top-left of the dashboard and centered on the [image widget](https://docs.datadoghq.com/dashboards/widgets/image/).

The suggested height for logos is around 12 grid units.

### Labels

Labels are created from the [Notes & Links](https://docs.datadoghq.com/dashboards/widgets/note/) widget type.

#### Metric Categories
Labels are used to divide the screenboard in visually comprehensive sections. 

- Category labels have gray backgrounds to contrast with the board and widgets.
- Text is 18px and horizontally centered. 

    !!! important
        Do not use bold or all capitalized letters because it can make the dashboard harder to read.

- Horizontal labels should be kept above the graphs and their width should be the length of the entire section. 

- For vertical labels, keep the label to the left of the section and its length should be the height the graphs. 
Enable a pointer to properly convey the direction of the section. 

- If there is a corresponding Datadog blog post, category names should be linked to the relevant section of the article.

#### Subcategories
With large sections of metric widgets, use subcategory labels to provide additional context. 
An example subcategory is grouping reads and writes metrics.

- Subcategory labels have blue backgrounds.
- Text is 16px and horizontally centered.
- Subcategory labels have the same rules as [metric category labels](./dashboards.md#metric-categories).

#### Notes
Labels can also be used as memos to describe a section or metric.

- Notes have the background color of yellow.
- Text must be 14px, left alignment, and not bold.

#### Other technologies
Some integrations are closely related to other technologies. 
Screenboards that contain metrics from other integration should use a different style to differentiate the products.

- Labels for the external technologies have pink backgrounds.
- Text must be 18px (consistent with other metric category labels), horizontally centered, and not bold.
- These labels have the same rules as [metric category labels](./dashboards.md#metric-categories).

### Widgets 
The suggested separation between widgets is:

- 2 grid units between different categories
- 1 grid unit between graphs of the same category

!!! important
    Widgets of the same type must be the same size and consistently aligned across the dashboard.

#### Graph titles

Graph titles summarize the queried metric.

- Titles are aligned to the left.
- Do not include timeframes (e.g "Average latency of the past day") because it's already indicated on the graph itself.
- Do not indicate the unit in the graph title because unit types are displayed automatically from metadata. 
An exception to this is if the calculation of the query represents a different type of unit.

#### Metrics

There are different types of metric widgets. The most commonly used are [timeseries](https://docs.datadoghq.com/dashboards/widgets/timeseries/),
 [query values](https://docs.datadoghq.com/dashboards/widgets/query_value/), and [tables](https://docs.datadoghq.com/dashboards/widgets/table/).
 
For more information on the available widget types, see the [list of supported dashboard widgets](https://docs.datadoghq.com/dashboards/widgets/).

!!! note
    Metric widgets usually have a timeframe of 4 hours. Query value widgets have the timeframe of 1 hour.
    
##### Timeseries

Timeseries widgets allow you to visualize the evolution of one or more metrics over time. 

###### Color Palette

| Types of metrics | Palette |
| ---------------- | ------------- |
| Errors/negative (e.g. Queued requests) | Warm or orange color |
| Memory | Cool or blue color |
| Read | Green color |
| Write | Purple color |

###### Display type

| Types of metrics | Display Type |
| ---------------- | ------------- |
| Volume (e.g. Number of connections) | `area` |
| Counts (e.g. Number of errors) | `bars` |
| Multiple groups or default | `lines` |


### Event stream

Add an event stream only if the service monitored by the dashboard is reporting events. Use `sources:service_name`.

!!! note
    Event stream widgets typically have a timeframe of 1 week.

### Template Variables

[Template variables](https://docs.datadoghq.com/dashboards/template_variables/) allow you to dynamically filter one or more widgets in a dashboard.

- Template variables must be universal and accessible by any user or account using the monitored service.
- Make sure all relevant graphs are listening to the relevant template variable filters.

!!! tip
    Adding `*=scope` as a tempoate variable is useful since users can access all their own tags.
    

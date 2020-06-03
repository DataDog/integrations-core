# Dashboards

-----

Datadog dashboards enable you to efficiently monitor your infrastructure and integrations
 by displaying and tracking key metrics.

## Best Practices

![Mongo dashboard](https://raw.githubusercontent.com/DataDog/integrations-core/master/docs/developer/assets/images/mongo_dashboard.png)

1. When creating a new dashboard, select the Screenboard type.

    !!! information
        Integration preset (or out of the box) dashboards are typically screenboards because they allow images, widgets, and labels. 
        Learn more about Datadog dashboards and see the differences between [screenboards and timeboards](https://docs.datadoghq.com/dashboards/#screenboard-vs-timeboard). 

1. Research the metrics supported by the integration and consider grouping them in relevant categories. 
Important metrics that are key to the performance and overview of the integration should be at the top.

    In the Mongo dashboard example, metrics are grouped by `Throughput`, `Resource saturation`, `Resource utilization`, and `Performance & Errors`.

1. Ensure good design by keeping labels and widgets aligned with consistent spacing and reasonable size. 

### Labels

Labels are created from the widget type [Notes & Links](https://docs.datadoghq.com/dashboards/widgets/note/).

#### Metric Categories
Labels are used to divide the screenboard in visually comprehensive sections. 

- Category labels have gray backgrounds to contrast with the board and widgets.
- Keep text at 18px, horizontally centered. 

    Do not use bold or all capitalized letters because it can make the dashboard harder to read and seem crowded.

- Horizontal labels should be kept above the graphs and be the length of the entire section. 
See the `Throughput` or `Resource saturation` labels in the Mongo dashboard.

    If the label is vertical, keep the label to the left of the graphs and it's length should be the height the graphs. 
Enable the right pointer to properly convey the direction of the section. See `Resource utilization` or `Performance & Errors` labels in the Mongo dashboard.

- If there is a corresponding Datadog blog post, category names should be linked to the relevant section of the article.

#### Subcategories
With large sections of metric widgets, use subcategory labels to provide additional context. 
Some subcategory examples are grouping reads and writes metrics.

- Subcategoy labels have blue backgrounds.
- Text is 16px, horizontally centered.
- Subcategory labels have the same rules as [Metric Category labels](./dashboards.md#metric-categories).

#### Notes
Labels can also be used as memos to describe a section or metric.

- Notes have the background color of yellow.
- Text must be 14px, left alignment, and not bold.

#### Other technologies
Some integrations are closely related to other technologies. 
Screenboards that contain metrics from other integration should use a different style to differentiate the products.

- Labels for the external technologies have pink backgrounds.
- Text must be 18px (consistent with other metric category labels), horizontally centered, and not bold.
- These labels have the same rules as [Metric Category labels](./dashboards.md#metric-categories).

### Metrics

Metrics have different types.
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

    In the Mongo dashboard example, metrics are grouped by Throughput, Resource saturation, Resource utilization, and Performance & Errors.

1. Ensure good design by keeping labels and widgets aligned with consistent spacing and reasonable size. 

### Labels

Labels are used to divide the screenboard in easy to understand sections. 

- Labels have gray backgrounds to contrast with the board and widgets.
- Keep text at 18px, horizontally centered. 
Do not use bold or all capitalized because it can make the dashboard harder to read and seem crowded.
- Horizontal labels should be kept above the graphs and be the length of the entire section. 
See the Throughput or Resource Saturation labels in the Mongo dashboard.

    If the label is vertical, keep the label to the left of the graphs and it's length should be the height the graphs. 
Enable the right pointer to properly convey the direction of the section. See Resource utilization or Performance & Errors labels in the Mongo dashboard.

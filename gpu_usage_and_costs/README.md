# GPU Usage and Costs

## Overview

The GPU Usage and Costs integration provides visibility into GPU compute spend across AWS, Azure, and GCP. Use it to monitor spend breakdowns by instance type and team, track pricing coverage, identify unused GPU capacity, and attribute costs.

This integration works with Datadog [Cloud Cost Management][1] to surface GPU-specific cost data, enabling your teams to:

- **Track GPU spend** across all major cloud providers in a single view
- **Identify unused GPU capacity** and reduce waste
- **Attribute costs** to teams and workloads for accurate chargeback
- **Monitor trends** in GPU instance pricing and utilization

## Setup

Enable [Cloud Cost Management][1] for your cloud accounts. GPU cost data is automatically available once cloud cost data is flowing.

## Data Collected

### Metrics

GPU Usage and Costs does not emit its own metrics. It uses cloud cost metrics (`aws.cost.amortized`, `azure.cost.amortized`, `gcp.cost.amortized`) filtered to GPU instance types.

### Service Checks

GPU Usage and Costs does not include any service checks.

### Events

GPU Usage and Costs does not include any events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://docs.datadoghq.com/cloud_cost_management/
[2]: https://docs.datadoghq.com/help/

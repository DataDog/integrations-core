## Overview

Red Hat OpenShift is an open source container application platform based on the Kubernetes container orchestrator for enterprise application development and deployment.

## Setup

Datadog's [Kubernetes integration][1] supports OpenShift versions 3.3 and up. No additional setup is required for OpenShift-specific tags to be collected.

[Cluster resource quota][2] metrics are collected by the leader Agent. Configure the Agent [event collection and leader election][3] in order to send metrics to Datadog.

## Data Collected
### Metrics

See [metadata.csv][4] for a list of metrics provided by this check.

### Events
The OpenShift check does not include any events at this time.

### Service Checks

The OpenShift check does not include any Service Checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].


[1]: https://docs.datadoghq.com/integrations/kubernetes/
[2]: https://docs.openshift.com/container-platform/3.9/admin_guide/multiproject_quota.html
[3]: https://docs.datadoghq.com/agent/basic_agent_usage/kubernetes/#event-collection
[4]: https://github.com/DataDog/integrations-core/blob/master/openshift/metadata.csv
[5]: https://docs.datadoghq.com/help/

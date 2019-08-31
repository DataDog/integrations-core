## Overview
Red Hat OpenShift is an open source container application platform based on the Kubernetes container orchestrator for enterprise application development and deployment.

## Setup
Starting with version 6.1, the Datadog Agent supports monitoring OpenShift Origin and Enterprise clusters. Depending on your needs and the security constraints of your cluster, three deployment scenarios are supported:

* [Restricted SCC operations][1]
* [Host network SCC operations][2]
* [Custom Datadog SCC for all features][3]

Information on security context constraints is available in the [Agent documentation][4].

### General Information
* Refer to the common installation instructions for the [Docker Agent][5] and the [Kubernetes section][6].
* The [Kubernetes integration][7] targets OpenShift 3.7.0+ by default. Datadog relies on features and endpoints introduced in this version. [More installation steps][8] are required for older versions.
* [Cluster resource quota][9] metrics are collected by the leader Agent. Configure the Agent [event collection and leader election][10] in order to send metrics to Datadog.

## Data Collected
### Metrics

See [metadata.csv][11] for a list of metrics provided by this check.

### Events
The OpenShift check does not include any events.

### Service Checks
The OpenShift check does not include any Service Checks.

## Troubleshooting
Need help? Contact [Datadog support][12].


[1]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/OPENSHIFT.md#restricted-scc-operations
[2]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/OPENSHIFT.md#host-network-scc-operations
[3]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/OPENSHIFT.md#custom-datadog-scc-for-all-features
[4]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/OPENSHIFT.md#openshift-installation-and-configuration-instructions
[5]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/README.md
[6]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/README.md#Kubernetes
[7]: https://docs.datadoghq.com/integrations/kubernetes
[8]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/README.md#legacy-kubernetes-versions
[9]: https://docs.openshift.com/container-platform/3.9/admin_guide/multiproject_quota.html
[10]: https://docs.datadoghq.com/agent/kubernetes/event_collection
[11]: https://github.com/DataDog/integrations-core/blob/master/openshift/metadata.csv
[12]: https://docs.datadoghq.com/help

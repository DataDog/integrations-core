## Overview
Red Hat OpenShift is an open source container application platform based on the Kubernetes container orchestrator for enterprise application development and deployment.

## Setup
Starting with version 6.1, the Datadog Agent supports monitoring OpenShift Origin and Enterprise clusters. Depending on your needs and the security constraints of your cluster, three deployment scenarios are supported:

* [Restricted SCC operations][10]
* [Host network SCC operations][11]
* [Custom Datadog for all features][12]

Information on security context constraints is available in the [Agent documentation][9].

### General Information
* Refer to the common installation instructions for the [Docker Agent][7] and the [Kubernetes section][8].
* The [Kubernetes integration][1] targets OpenShift 3.7.0+ by default. Datadog relies on features and endpoints introduced in this version. [More installation steps][6] are required for older versions.
* [Cluster resource quota][2] metrics are collected by the leader Agent. Configure the Agent [event collection and leader election][3] in order to send metrics to Datadog.

## Data Collected
### Metrics

See [metadata.csv][4] for a list of metrics provided by this check.

### Events
The OpenShift check does not include any events.

### Service Checks
The OpenShift check does not include any Service Checks.

## Troubleshooting
Need help? Contact [Datadog support][5].


[1]: https://docs.datadoghq.com/integrations/kubernetes
[2]: https://docs.openshift.com/container-platform/3.9/admin_guide/multiproject_quota.html
[3]: https://docs.datadoghq.com/agent/kubernetes/event_collection/
[4]: https://github.com/DataDog/integrations-core/blob/master/openshift/metadata.csv
[5]: https://docs.datadoghq.com/help
[6]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/README.md#legacy-kubernetes-versions
[7]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/README.md
[8]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/README.md#Kubernetes
[9]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/OPENSHIFT.md#openshift-installation-and-configuration-instructions
[10]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/OPENSHIFT.md#restricted-scc-operations
[11]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/OPENSHIFT.md#host-network-scc-operations
[12]: https://github.com/DataDog/datadog-agent/blob/master/Dockerfiles/agent/OPENSHIFT.md#custom-datadog-scc-for-all-features

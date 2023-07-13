# CHANGELOG - kubernetes

## 1.7.0 / 2020-05-17

***Added***:

* Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.6.0 / 2020-01-13

***Added***:

* Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 1.5.1 / 2018-09-04

***Fixed***:

* Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).
* Only calculate filesystem usage when capacity is greater than 0. See [#1606](https://github.com/DataDog/integrations-core/pull/1606). Thanks [aaronbbrown](https://github.com/aaronbbrown).

## 1.5.0 / 2017-10-10

***Fixed***:
* remove namespace from pod_name tag. See [#770](https://github.com/DataDog/integrations-core/issues/770)
* stop reporting cAdvisor metrics about non-container objects. See [#770](https://github.com/DataDog/integrations-core/issues/770)

## 1.4.0 / 2017-09-12

***Added***:

* Add an option to retry kubelet connection if it's not up at start time. See [#722](https://github.com/DataDog/integrations-core/issues/722)

***Fixed***:

* fix container_image names reported as sha checksums [#731](https://github.com/DataDog/integrations-core/issues/731)

## 1.3.0 / 2017-08-28

***Added***:

* add an option to collect node labels as host tags. See [#614](https://github.com/DataDog/integrations-core/issues/614)
* add custom tags to service checks [#642](https://github.com/DataDog/integrations-core/issues/642)
* skip cAdvisor metrics if port is set to 0. See [#655](https://github.com/DataDog/integrations-core/issues/655)
* enable event collection according to agent leader status. See [#687](https://github.com/DataDog/integrations-core/issues/687)

## 1.2.0 / 2017-07-18

***Added***:

* allow to configure kubelet and apiserver urls and credentials to run directly on the host. See [#508](https://github.com/DataDog/integrations-core/issues/508)
* query kubernetes service mapping every 5 minutes to reduce apiserver traffic (see service_tag_update_freq option) and add collect_service_tags option to disable it completely. See [#476](https://github.com/DataDog/integrations-core/issues/476)

***Fixed***:

* fix failures when the spec has "has_filesystem" entry but no stats entry for filesystem. See [#494](https://github.com/DataDog/integrations-core/issues/494)
* don't fail if cadvisor is unreachable, send integration warning and send other metrics. See [#538](https://github.com/DataDog/integrations-core/issues/538)
* Fix typo in exception reporting when unable to collect metrics for a container. See [#493](https://github.com/DataDog/integrations-core/issues/493)

## 1.1.0 / 2017-06-05

***Added***:

* Make the pod label to tag prefix configurable. See [dd-agent-3345](https://github.com/DataDog/dd-agent/pull/3345)
* Report a service check when the Kubelet daemon is unreachable. See [#350](https://github.com/DataDog/integrations-core/issues/350)
* Add service and creator (deployment/daemon_set/replica_set/job) tags to kube.* and docker.* metrics. See [#319](https://github.com/DataDog/integrations-core/issues/319) and [#434](https://github.com/DataDog/integrations-core/issues/434)
* Add custom tags to events. See [#449](https://github.com/DataDog/integrations-core/issues/449)

***Fixed***:

* Fix missing docker.net metrics in Kubernetes. See [#418](https://github.com/DataDog/integrations-core/issues/418)

## 1.0.0 / 2017-02-23

***Added***:

* adds Kubernetes integration.

# CHANGELOG - kubelet

## 1.3.1 / 2018-06-08

* [Changed] Kubelet check: better encapsulate the pod list retrieval. See [#1648](https://github.com/DataDog/integrations-core/pull/1648).

## 1.3.0 / 2018-06-07

* [Added] Support for gathering metrics from prometheus endpoint for the kubelet itself.. See [#1581](https://github.com/DataDog/integrations-core/pull/1581).

## 1.2.0 / 2018-05-11

* [FEATURE] Collect metrics directly from cadvisor, for kubenetes version older than 1.7.6. See [#1339][]
* [FEATURE] Add instance tags to all metrics. Improve the coverage of the check. See [#1377][]
* [BUGFIX] Reports nanocores instead of cores. See [#1361][]
* [FEATURE] Allow to disable prometheus metric collection. See [#1423][]
* [FEATURE] Container metrics now respect the container filtering rules. Requires Agent 6.2+. See [#1442][]
* [BUGFIX] Fix submission of CPU metrics on multi-threaded containers. See [#1489][]
* [BUGFIX] Fix SSL when specifying certificate files

## 1.1.0 / 2018-03-23

* [FEATURE] Support TLS

## 1.0.0 / 2018-02-28

* [FEATURE] add kubelet integration.

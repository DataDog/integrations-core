# CHANGELOG - kubelet

## 2.3.1 / 2019-01-04

* [Fixed] document kubernetes.pods.running and kubernetes.containers.running. See [#2792](https://github.com/DataDog/integrations-core/pull/2792).
* [Fixed] Fix default yaml instance. See [#2756](https://github.com/DataDog/integrations-core/pull/2756).
* [Fixed] Make the check robust to an unresponsive kubelet. See [#2719](https://github.com/DataDog/integrations-core/pull/2719).

## 2.3.0 / 2018-11-30

* [Added] Add restart and container state metrics to kubelet. See [#2605](https://github.com/DataDog/integrations-core/pull/2605). Thanks [schleyfox](https://github.com/schleyfox).
* [Added] Add more cpu metrics. See [#2595](https://github.com/DataDog/integrations-core/pull/2595).
* [Added] Add kubelet volume metrics. See [#2256](https://github.com/DataDog/integrations-core/pull/2256). Thanks [derekchan](https://github.com/derekchan).
* [Fixed] [kubelet] correctly ignore pods that are neither running or pending for resource limits&requests. See [#2597](https://github.com/DataDog/integrations-core/pull/2597).

## 2.2.0 / 2018-10-12

* [Added] Add kubelet rss and working set memory metrics. See [#2390](https://github.com/DataDog/integrations-core/pull/2390).

## 2.1.0 / 2018-10-10

* [Fixed] Fix parsing errors when the podlist is in an inconsistent state. See [#2338](https://github.com/DataDog/integrations-core/pull/2338).
* [Fixed] Fix kubelet input filtering. See [#2344](https://github.com/DataDog/integrations-core/pull/2344).
* [Fixed] Fix pod metric filtering for containerd. See [#2283](https://github.com/DataDog/integrations-core/pull/2283).
* [Added] Add additional kubelet metrics. See [#2245](https://github.com/DataDog/integrations-core/pull/2245).
* [Added] Add the kubernetes.containers.running metric. See [#2191](https://github.com/DataDog/integrations-core/pull/2191). Thanks [Devatoria](https://github.com/Devatoria).

## 2.0.0 / 2018-09-04

* [Changed] Update kubelet to use the new OpenMetricsBaseCheck. See [#1982](https://github.com/DataDog/integrations-core/pull/1982).
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093](https://github.com/DataDog/integrations-core/pull/2093).
* [Changed] Get pod & container IDs from the pod list for reliability. See [#1996](https://github.com/DataDog/integrations-core/pull/1996).
* [Fixed] Fixing typo in the pod list path used in the kubelet integration . See [#1847](https://github.com/DataDog/integrations-core/pull/1847).
* [Fixed] Fix network and disk metric collection when multiple devices are used by a container. See [#1894](https://github.com/DataDog/integrations-core/pull/1894).
* [Fixed] Improve check performance by filtering it's input before parsing. See [#1875](https://github.com/DataDog/integrations-core/pull/1875).
* [Fixed] Reduce log spam on kubernetes tagging. See [#1830](https://github.com/DataDog/integrations-core/pull/1830).
* [Fixed] Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).

## 1.4.0 / 2018-06-14

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

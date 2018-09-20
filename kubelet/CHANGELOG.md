# CHANGELOG - kubelet

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

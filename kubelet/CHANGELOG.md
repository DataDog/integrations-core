# CHANGELOG - kubelet

## 2.3.2 / 2019-02-05

* [Fixed] Collect memory usage and filesystem usage for static pods. See [#XXX]

## 2.3.1 / 2019-01-04

* [Fixed] document kubernetes.pods.running and kubernetes.containers.running. See [#2792][1].
* [Fixed] Fix default yaml instance. See [#2756][2].
* [Fixed] Make the check robust to an unresponsive kubelet. See [#2719][3].

## 2.3.0 / 2018-11-30

* [Added] Add restart and container state metrics to kubelet. See [#2605][4]. Thanks [schleyfox][5].
* [Added] Add more cpu metrics. See [#2595][6].
* [Added] Add kubelet volume metrics. See [#2256][7]. Thanks [derekchan][8].
* [Fixed] [kubelet] correctly ignore pods that are neither running or pending for resource limits&requests. See [#2597][9].

## 2.2.0 / 2018-10-12

* [Added] Add kubelet rss and working set memory metrics. See [#2390][10].

## 2.1.0 / 2018-10-10

* [Fixed] Fix parsing errors when the podlist is in an inconsistent state. See [#2338][11].
* [Fixed] Fix kubelet input filtering. See [#2344][12].
* [Fixed] Fix pod metric filtering for containerd. See [#2283][13].
* [Added] Add additional kubelet metrics. See [#2245][14].
* [Added] Add the kubernetes.containers.running metric. See [#2191][15]. Thanks [Devatoria][16].

## 2.0.0 / 2018-09-04

* [Changed] Update kubelet to use the new OpenMetricsBaseCheck. See [#1982][17].
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][18].
* [Changed] Get pod & container IDs from the pod list for reliability. See [#1996][19].
* [Fixed] Fixing typo in the pod list path used in the kubelet integration . See [#1847][20].
* [Fixed] Fix network and disk metric collection when multiple devices are used by a container. See [#1894][21].
* [Fixed] Improve check performance by filtering it's input before parsing. See [#1875][22].
* [Fixed] Reduce log spam on kubernetes tagging. See [#1830][23].
* [Fixed] Add data files to the wheel package. See [#1727][24].

## 1.4.0 / 2018-06-14

* [Changed] Kubelet check: better encapsulate the pod list retrieval. See [#1648][25].

## 1.3.0 / 2018-06-07

* [Added] Support for gathering metrics from prometheus endpoint for the kubelet itself.. See [#1581][26].

## 1.2.0 / 2018-05-11

* [FEATURE] Collect metrics directly from cadvisor, for kubenetes version older than 1.7.6. See [#1339][27]
* [FEATURE] Add instance tags to all metrics. Improve the coverage of the check. See [#1377][28]
* [BUGFIX] Reports nanocores instead of cores. See [#1361][29]
* [FEATURE] Allow to disable prometheus metric collection. See [#1423][30]
* [FEATURE] Container metrics now respect the container filtering rules. Requires Agent 6.2+. See [#1442][31]
* [BUGFIX] Fix submission of CPU metrics on multi-threaded containers. See [#1489][32]
* [BUGFIX] Fix SSL when specifying certificate files

## 1.1.0 / 2018-03-23

* [FEATURE] Support TLS

## 1.0.0 / 2018-02-28

* [FEATURE] add kubelet integration.
[1]: https://github.com/DataDog/integrations-core/pull/2792
[2]: https://github.com/DataDog/integrations-core/pull/2756
[3]: https://github.com/DataDog/integrations-core/pull/2719
[4]: https://github.com/DataDog/integrations-core/pull/2605
[5]: https://github.com/schleyfox
[6]: https://github.com/DataDog/integrations-core/pull/2595
[7]: https://github.com/DataDog/integrations-core/pull/2256
[8]: https://github.com/derekchan
[9]: https://github.com/DataDog/integrations-core/pull/2597
[10]: https://github.com/DataDog/integrations-core/pull/2390
[11]: https://github.com/DataDog/integrations-core/pull/2338
[12]: https://github.com/DataDog/integrations-core/pull/2344
[13]: https://github.com/DataDog/integrations-core/pull/2283
[14]: https://github.com/DataDog/integrations-core/pull/2245
[15]: https://github.com/DataDog/integrations-core/pull/2191
[16]: https://github.com/Devatoria
[17]: https://github.com/DataDog/integrations-core/pull/1982
[18]: https://github.com/DataDog/integrations-core/pull/2093
[19]: https://github.com/DataDog/integrations-core/pull/1996
[20]: https://github.com/DataDog/integrations-core/pull/1847
[21]: https://github.com/DataDog/integrations-core/pull/1894
[22]: https://github.com/DataDog/integrations-core/pull/1875
[23]: https://github.com/DataDog/integrations-core/pull/1830
[24]: https://github.com/DataDog/integrations-core/pull/1727
[25]: https://github.com/DataDog/integrations-core/pull/1648
[26]: https://github.com/DataDog/integrations-core/pull/1581
[27]: 
[28]: 
[29]: 
[30]: 
[31]: 
[32]: 

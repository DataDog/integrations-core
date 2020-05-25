# CHANGELOG - kubelet

## 4.1.0 / 2020-05-17

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add parsing from `/stats/summary` for Windows. See [#6497](https://github.com/DataDog/integrations-core/pull/6497).
* [Added] Expose number of cfs enforcement periods. See [#6093](https://github.com/DataDog/integrations-core/pull/6093). Thanks [adammw](https://github.com/adammw).

## 4.0.0 / 2020-04-04

* [Fixed] Update prometheus_client. See [#6200](https://github.com/DataDog/integrations-core/pull/6200).
* [Fixed] Fix support for kubernetes v1.18. See [#6203](https://github.com/DataDog/integrations-core/pull/6203).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Changed] Pass namespace to `is_excluded`. See [#6217](https://github.com/DataDog/integrations-core/pull/6217).

## 3.6.0 / 2020-02-22

* [Added] Add pod tags to volume metrics. See [#5453](https://github.com/DataDog/integrations-core/pull/5453).

## 3.5.2 / 2020-01-31

* [Fixed] Ignore insecure warnings for kubelet requests. See [#5607](https://github.com/DataDog/integrations-core/pull/5607).

## 3.5.1 / 2020-01-15

* [Fixed] Fix Kubelet credentials handling. See [#5455](https://github.com/DataDog/integrations-core/pull/5455).

## 3.5.0 / 2020-01-13

* [Fixed] Improve url join to not mutate the base url when proxying a call. See [#5416](https://github.com/DataDog/integrations-core/pull/5416).
* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).
* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Add log filesystem container metric. See [#5383](https://github.com/DataDog/integrations-core/pull/5383).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Added] Add kubelet and runtime cpu and mem metrics. See [#5370](https://github.com/DataDog/integrations-core/pull/5370).
* [Added] Update metrics for >= 1.14. See [#5336](https://github.com/DataDog/integrations-core/pull/5336).

## 3.4.0 / 2019-12-02

* [Added] Collect a new metric: kubelet.evictions. See [#5076](https://github.com/DataDog/integrations-core/pull/5076).
* [Added] Add a gauge for effective usage of ephemeral storage per POD. See [#5052](https://github.com/DataDog/integrations-core/pull/5052).

## 3.3.4 / 2019-10-30

* [Fixed] Fix container collection for k8s 1.16. See [#4925](https://github.com/DataDog/integrations-core/pull/4925).

## 3.3.3 / 2019-10-11

* [Fixed] Send kubelet metrics with tags only. See [#4659](https://github.com/DataDog/integrations-core/pull/4659).

## 3.3.2 / 2019-08-14

* [Fixed] Enforce unicode output in requests.iter_lines call. See [#4360](https://github.com/DataDog/integrations-core/pull/4360).

## 3.3.1 / 2019-07-16

* [Fixed] Update tagger usage to match prefix update. See [#4109](https://github.com/DataDog/integrations-core/pull/4109).

## 3.3.0 / 2019-07-04

* [Added] Add swap memory checks to cadvisor kubelet checks. See [#3808](https://github.com/DataDog/integrations-core/pull/3808). Thanks [adammw](https://github.com/adammw).

## 3.2.1 / 2019-06-28

* [Fixed] Make the kubelet and ECS fargate checks resilient to the tagger returning None. See [#4004](https://github.com/DataDog/integrations-core/pull/4004).

## 3.2.0 / 2019-06-13

* [Fixed] Revert "Collect network usage metrics (#3740)". See [#3914](https://github.com/DataDog/integrations-core/pull/3914).

## 3.1.0 / 2019-05-14

* [Added] Collect network usage metrics. See [#3740](https://github.com/DataDog/integrations-core/pull/3740).
* [Added] add useful prometheus labels to metric tags. See [#3735](https://github.com/DataDog/integrations-core/pull/3735).
* [Added] Adhere to code style. See [#3525](https://github.com/DataDog/integrations-core/pull/3525).

## 3.0.1 / 2019-04-04

* [Fixed] Fix podlist multiple iterations when using pod expiration. See [#3456](https://github.com/DataDog/integrations-core/pull/3456).
* [Fixed] Fix health check during first check run. See [#3457](https://github.com/DataDog/integrations-core/pull/3457).

## 3.0.0 / 2019-03-29

* [Changed] Do not tag container restarts/state metrics by container_id anymore. See [#3424](https://github.com/DataDog/integrations-core/pull/3424).
* [Added] Allow to filter out old pods when parsing the podlist to reduce memory usage. See [#3189](https://github.com/DataDog/integrations-core/pull/3189).

## 2.4.0 / 2019-02-18

* [Fixed] Fix usage metrics collection for static pods. See [#3079](https://github.com/DataDog/integrations-core/pull/3079).
* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).
* [Added] Support Python 3. See [#3028](https://github.com/DataDog/integrations-core/pull/3028).
* [Fixed] Fix pods/container.running metrics to exclude non running ones. See [#3025](https://github.com/DataDog/integrations-core/pull/3025).

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

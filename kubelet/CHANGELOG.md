# CHANGELOG - kubelet

## 7.5.2 / 2022-12-09

* [Fixed] Set the `prometheus_url` for the kubelet endpoints in the `__init__` function. See [#13360](https://github.com/DataDog/integrations-core/pull/13360).

## 7.5.1 / 2022-10-28 / Agent 7.41.0

* [Fixed] Ignore aberrant values for `kubernetes.memory.rss`. See [#13076](https://github.com/DataDog/integrations-core/pull/13076).

## 7.5.0 / 2022-09-16 / Agent 7.40.0

* [Added] Update HTTP config spec templates. See [#12890](https://github.com/DataDog/integrations-core/pull/12890).
* [Added] Add `CreateContainerError` and `InvalidImageName` to waiting reasons. See [#12758](https://github.com/DataDog/integrations-core/pull/12758).

## 7.4.1 / 2022-08-05 / Agent 7.39.0

* [Fixed] Fix probe metrics collection when credentials are required. See [#12642](https://github.com/DataDog/integrations-core/pull/12642).

## 7.4.0 / 2022-05-15 / Agent 7.37.0

* [Added] Support dynamic bearer tokens (Bound Service Account Token Volume). See [#11915](https://github.com/DataDog/integrations-core/pull/11915).
* [Fixed] Fix kubernetes.memory.limits on kind clusters. See [#11914](https://github.com/DataDog/integrations-core/pull/11914).
* [Fixed] Sanitize the `url` tag. See [#11989](https://github.com/DataDog/integrations-core/pull/11989).
* [Fixed] Apply container filter to `kubernetes.kubelet.container.log_filesystem.used_bytes`. See [#11974](https://github.com/DataDog/integrations-core/pull/11974).

## 7.3.1 / 2022-04-11 / Agent 7.36.0

* [Fixed] Handle probe metrics when the endpoint is not available (Kubernetes < 1.15). See [#11807](https://github.com/DataDog/integrations-core/pull/11807).

## 7.3.0 / 2022-04-05

* [Added] Collect liveness and readiness probe metrics. See [#11682](https://github.com/DataDog/integrations-core/pull/11682).
* [Added] Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).
* [Added] Add pleg metrics. See [#11616](https://github.com/DataDog/integrations-core/pull/11616).
* [Fixed] Support newer versions of `click`. See [#11746](https://github.com/DataDog/integrations-core/pull/11746).
* [Fixed] Remove outdated warning in the description for the `tls_ignore_warning` option. See [#11591](https://github.com/DataDog/integrations-core/pull/11591).

## 7.2.1 / 2022-02-24 / Agent 7.35.0

* [Fixed] Apply namespace exclusion rules in cadvisor and summary metrics. See [#11559](https://github.com/DataDog/integrations-core/pull/11559).

## 7.2.0 / 2022-02-19

* [Added] Add `pyproject.toml` file. See [#11386](https://github.com/DataDog/integrations-core/pull/11386).
* [Added] Update example config. See [#11515](https://github.com/DataDog/integrations-core/pull/11515).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).
* [Fixed] Apply namespace exclusion rules for volume metrics. See [#11512](https://github.com/DataDog/integrations-core/pull/11512).

## 7.1.1 / 2022-01-08 / Agent 7.34.0

* [Fixed] Do not drop the first kubelet eviction event. See [#11032](https://github.com/DataDog/integrations-core/pull/11032).

## 7.1.0 / 2021-10-04 / Agent 7.32.0

* [Added] Add allow_redirect option. See [#10160](https://github.com/DataDog/integrations-core/pull/10160).
* [Fixed] Apply namespace exclusion rules before reporting network metrics. See [#10237](https://github.com/DataDog/integrations-core/pull/10237).
* [Fixed] Bump base package dependency. See [#10218](https://github.com/DataDog/integrations-core/pull/10218).
* [Fixed] Don't call the tagger for pods not running. See [#10030](https://github.com/DataDog/integrations-core/pull/10030).

## 7.0.0 / 2021-05-28 / Agent 7.29.0

* [Changed] Increase default scraping time from 15s to 20s. See [#9193](https://github.com/DataDog/integrations-core/pull/9193).

## 6.1.0 / 2021-04-19 / Agent 7.28.0

* [Added] Allow configurability of the ignore_metrics option. See [#9161](https://github.com/DataDog/integrations-core/pull/9161).

## 6.0.0 / 2021-04-14

* [Added] Add logic to enable/disable metrics collected from the summary endpoint. See [#9155](https://github.com/DataDog/integrations-core/pull/9155).
* [Changed] Refactor kubelet and eks_fargate checks to use `KubeletBase`. See [#8798](https://github.com/DataDog/integrations-core/pull/8798).

## 5.2.0 / 2021-03-07 / Agent 7.27.0

* [Added] Add new metrics. See [#8562](https://github.com/DataDog/integrations-core/pull/8562).
* [Fixed] Fix TypeError when retrieved pod_list is occasionally None. See [#8530](https://github.com/DataDog/integrations-core/pull/8530).
* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 5.1.0 / 2021-01-25 / Agent 7.26.0

* [Added] Add new default for newly autodiscovered checks. See [#8177](https://github.com/DataDog/integrations-core/pull/8177).

## 5.0.0 / 2020-09-21 / Agent 7.23.0

* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).
* [Changed] Replace InsecureRequestWarning with standard logs. See [#7512](https://github.com/DataDog/integrations-core/pull/7512).
* [Changed] Improve the kubelet check error reporting in the output of `agent status`. See [#7495](https://github.com/DataDog/integrations-core/pull/7495).

## 4.1.1 / 2020-06-29 / Agent 7.21.0

* [Fixed] Fix missing metrics for static pods. See [#6736](https://github.com/DataDog/integrations-core/pull/6736).

## 4.1.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add parsing from `/stats/summary` for Windows. See [#6497](https://github.com/DataDog/integrations-core/pull/6497).
* [Added] Expose number of cfs enforcement periods. See [#6093](https://github.com/DataDog/integrations-core/pull/6093). Thanks [adammw](https://github.com/adammw).

## 4.0.0 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update prometheus_client. See [#6200](https://github.com/DataDog/integrations-core/pull/6200).
* [Fixed] Fix support for kubernetes v1.18. See [#6203](https://github.com/DataDog/integrations-core/pull/6203).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Changed] Pass namespace to `is_excluded`. See [#6217](https://github.com/DataDog/integrations-core/pull/6217).

## 3.6.0 / 2020-02-22 / Agent 7.18.0

* [Added] Add pod tags to volume metrics. See [#5453](https://github.com/DataDog/integrations-core/pull/5453).

## 3.5.2 / 2020-01-31 / Agent 7.17.1

* [Fixed] Ignore insecure warnings for kubelet requests. See [#5607](https://github.com/DataDog/integrations-core/pull/5607).

## 3.5.1 / 2020-01-15 / Agent 7.17.0

* [Fixed] Fix Kubelet credentials handling. See [#5455](https://github.com/DataDog/integrations-core/pull/5455).

## 3.5.0 / 2020-01-13

* [Fixed] Improve url join to not mutate the base url when proxying a call. See [#5416](https://github.com/DataDog/integrations-core/pull/5416).
* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).
* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Add log filesystem container metric. See [#5383](https://github.com/DataDog/integrations-core/pull/5383).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Added] Add kubelet and runtime cpu and mem metrics. See [#5370](https://github.com/DataDog/integrations-core/pull/5370).
* [Added] Update metrics for >= 1.14. See [#5336](https://github.com/DataDog/integrations-core/pull/5336).

## 3.4.0 / 2019-12-02 / Agent 7.16.0

* [Added] Collect a new metric: kubelet.evictions. See [#5076](https://github.com/DataDog/integrations-core/pull/5076).
* [Added] Add a gauge for effective usage of ephemeral storage per POD. See [#5052](https://github.com/DataDog/integrations-core/pull/5052).

## 3.3.4 / 2019-10-30 / Agent 6.15.0

* [Fixed] Fix container collection for k8s 1.16. See [#4925](https://github.com/DataDog/integrations-core/pull/4925).

## 3.3.3 / 2019-10-11

* [Fixed] Send kubelet metrics with tags only. See [#4659](https://github.com/DataDog/integrations-core/pull/4659).

## 3.3.2 / 2019-08-14 / Agent 6.14.0

* [Fixed] Enforce unicode output in requests.iter_lines call. See [#4360](https://github.com/DataDog/integrations-core/pull/4360).

## 3.3.1 / 2019-07-16 / Agent 6.13.0

* [Fixed] Update tagger usage to match prefix update. See [#4109](https://github.com/DataDog/integrations-core/pull/4109).

## 3.3.0 / 2019-07-04

* [Added] Add swap memory checks to cadvisor kubelet checks. See [#3808](https://github.com/DataDog/integrations-core/pull/3808). Thanks [adammw](https://github.com/adammw).

## 3.2.1 / 2019-06-28 / Agent 6.12.1

* [Fixed] Make the kubelet and ECS fargate checks resilient to the tagger returning None. See [#4004](https://github.com/DataDog/integrations-core/pull/4004).

## 3.2.0 / 2019-06-13 / Agent 6.12.0

* [Fixed] Revert "Collect network usage metrics (#3740)". See [#3914](https://github.com/DataDog/integrations-core/pull/3914).

## 3.1.0 / 2019-05-14

* [Added] Collect network usage metrics. See [#3740](https://github.com/DataDog/integrations-core/pull/3740).
* [Added] add useful prometheus labels to metric tags. See [#3735](https://github.com/DataDog/integrations-core/pull/3735).
* [Added] Adhere to code style. See [#3525](https://github.com/DataDog/integrations-core/pull/3525).

## 3.0.1 / 2019-04-04 / Agent 6.11.0

* [Fixed] Fix podlist multiple iterations when using pod expiration. See [#3456](https://github.com/DataDog/integrations-core/pull/3456).
* [Fixed] Fix health check during first check run. See [#3457](https://github.com/DataDog/integrations-core/pull/3457).

## 3.0.0 / 2019-03-29

* [Changed] Do not tag container restarts/state metrics by container_id anymore. See [#3424](https://github.com/DataDog/integrations-core/pull/3424).
* [Added] Allow to filter out old pods when parsing the podlist to reduce memory usage. See [#3189](https://github.com/DataDog/integrations-core/pull/3189).

## 2.4.0 / 2019-02-18 / Agent 6.10.0

* [Fixed] Fix usage metrics collection for static pods. See [#3079](https://github.com/DataDog/integrations-core/pull/3079).
* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).
* [Added] Support Python 3. See [#3028](https://github.com/DataDog/integrations-core/pull/3028).
* [Fixed] Fix pods/container.running metrics to exclude non running ones. See [#3025](https://github.com/DataDog/integrations-core/pull/3025).

## 2.3.1 / 2019-01-04 / Agent 6.9.0

* [Fixed] document kubernetes.pods.running and kubernetes.containers.running. See [#2792][1].
* [Fixed] Fix default yaml instance. See [#2756][2].
* [Fixed] Make the check robust to an unresponsive kubelet. See [#2719][3].

## 2.3.0 / 2018-11-30 / Agent 6.8.0

* [Added] Add restart and container state metrics to kubelet. See [#2605][4]. Thanks [schleyfox][5].
* [Added] Add more cpu metrics. See [#2595][6].
* [Added] Add kubelet volume metrics. See [#2256][7]. Thanks [derekchan][8].
* [Fixed] [kubelet] correctly ignore pods that are neither running or pending for resource limits&requests. See [#2597][9].

## 2.2.0 / 2018-10-12 / Agent 6.6.0

* [Added] Add kubelet rss and working set memory metrics. See [#2390][10].

## 2.1.0 / 2018-10-10

* [Fixed] Fix parsing errors when the podlist is in an inconsistent state. See [#2338][11].
* [Fixed] Fix kubelet input filtering. See [#2344][12].
* [Fixed] Fix pod metric filtering for containerd. See [#2283][13].
* [Added] Add additional kubelet metrics. See [#2245][14].
* [Added] Add the kubernetes.containers.running metric. See [#2191][15]. Thanks [Devatoria][16].

## 2.0.0 / 2018-09-04 / Agent 6.5.0

* [Changed] Update kubelet to use the new OpenMetricsBaseCheck. See [#1982][17].
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][18].
* [Changed] Get pod & container IDs from the pod list for reliability. See [#1996][19].
* [Fixed] Fixing typo in the pod list path used in the kubelet integration . See [#1847][20].
* [Fixed] Fix network and disk metric collection when multiple devices are used by a container. See [#1894][21].
* [Fixed] Improve check performance by filtering it's input before parsing. See [#1875][22].
* [Fixed] Reduce log spam on kubernetes tagging. See [#1830][23].
* [Fixed] Add data files to the wheel package. See [#1727][24].

## 1.4.0 / 2018-06-14 / Agent 6.3.1

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
[27]: https://github.com/DataDog/integrations-core/pull/1339
[28]: https://github.com/DataDog/integrations-core/pull/1377
[29]: https://github.com/DataDog/integrations-core/pull/1361
[30]: https://github.com/DataDog/integrations-core/pull/1423
[31]: https://github.com/DataDog/integrations-core/pull/1442
[32]: https://github.com/DataDog/integrations-core/pull/1489

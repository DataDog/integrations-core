# CHANGELOG - kubelet

<!-- towncrier release notes start -->

## 7.13.1 / 2024-04-26

***Fixed***:

* Fixes pod resources requests/limits with exponent notation correctly, e.g. `129e6` for memory is `129M` / `123Mi` ([#17280](https://github.com/DataDog/integrations-core/pull/17280))

## 7.13.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Add logic to skip loading Python check in favor of core check based on config variable `DD_KUBELET_CORE_CHECK_ENABLED` ([#16856](https://github.com/DataDog/integrations-core/pull/16856))
* Emit kubelet metrics for init containers and pending pods ([#17035](https://github.com/DataDog/integrations-core/pull/17035))
* Bump the min base check version to 34.2.0 ([#17196](https://github.com/DataDog/integrations-core/pull/17196))

***Fixed***:

* Fix SSL error on kubelet check startup when talking to probes endpoint ([#16987](https://github.com/DataDog/integrations-core/pull/16987))

## 7.12.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 7.11.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 7.10.1 / 2023-11-14 / Agent 7.50.0

***Fixed***:

* Centralize `get_prometheus_url` function call in the init function and defer log warning after super() call. ([#16192](https://github.com/DataDog/integrations-core/pull/16192))

## 7.10.0 / 2023-11-10

***Added***:

* Added CreateContainerConfigError wait reason ([#16143](https://github.com/DataDog/integrations-core/pull/16143))

***Fixed***:

* Always define logger.
  Quick fix for https://github.com/DataDog/integrations-core/issues/16179. ([#16187](https://github.com/DataDog/integrations-core/pull/16187))

## 7.9.2 / 2023-09-29 / Agent 7.49.0

***Fixed***:

* Fix kubelet check failing to initialize when the kubelet is temporarily unavailable ([#15706](https://github.com/DataDog/integrations-core/pull/15706))

## 7.9.1 / 2023-08-18 / Agent 7.48.0

***Fixed***:

* Update datadog-checks-base dependency version to 32.6.0 ([#15604](https://github.com/DataDog/integrations-core/pull/15604))
* Fix Kubernetes probe metrics breaking in k8s 1.25+ ([#15254](https://github.com/DataDog/integrations-core/pull/15254))

## 7.9.0 / 2023-08-10

***Added***:

* add startup probe metrics ([#14570](https://github.com/DataDog/integrations-core/pull/14570))
* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 7.8.1 / 2023-07-13 / Agent 7.47.0

***Fixed***:

* Bump the minimum datadog-checks-base version ([#15218](https://github.com/DataDog/integrations-core/pull/15218))

## 7.8.0 / 2023-07-10

***Added***:

* Upgrade Pydantic model code generator ([#14779](https://github.com/DataDog/integrations-core/pull/14779))

***Fixed***:

* Fix Kubernetes probe total metrics type to gauge instead of count ([#15167](https://github.com/DataDog/integrations-core/pull/15167))
* kubelet: fallback from image to imageID to align with Go counterpart ([#15131](https://github.com/DataDog/integrations-core/pull/15131))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 7.7.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* [kubelet] Add node filesystem stat from stats/summary ([#14426](https://github.com/DataDog/integrations-core/pull/14426))

***Fixed***:

* Fix kubelet check failing to initialize when get_connection_info is empty ([#14546](https://github.com/DataDog/integrations-core/pull/14546))

## 7.6.0 / 2023-04-14 / Agent 7.45.0

***Added***:

* Adds container memory usage metrics from /stats/summary and kubelet memory usage ([#14150](https://github.com/DataDog/integrations-core/pull/14150))

***Fixed***:

* Support Ephemeral Percistent volume claim ([#14194](https://github.com/DataDog/integrations-core/pull/14194))

## 7.5.2 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Set the `prometheus_url` for the kubelet endpoints in the `__init__` function ([#13360](https://github.com/DataDog/integrations-core/pull/13360))

## 7.5.1 / 2022-10-28 / Agent 7.41.0

***Fixed***:

* Ignore aberrant values for `kubernetes.memory.rss` ([#13076](https://github.com/DataDog/integrations-core/pull/13076))

## 7.5.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))
* Add `CreateContainerError` and `InvalidImageName` to waiting reasons ([#12758](https://github.com/DataDog/integrations-core/pull/12758))

## 7.4.1 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Fix probe metrics collection when credentials are required ([#12642](https://github.com/DataDog/integrations-core/pull/12642))

## 7.4.0 / 2022-05-15 / Agent 7.37.0

***Added***:

* Support dynamic bearer tokens (Bound Service Account Token Volume) ([#11915](https://github.com/DataDog/integrations-core/pull/11915))

***Fixed***:

* Fix kubernetes.memory.limits on kind clusters ([#11914](https://github.com/DataDog/integrations-core/pull/11914))
* Sanitize the `url` tag ([#11989](https://github.com/DataDog/integrations-core/pull/11989))
* Apply container filter to `kubernetes.kubelet.container.log_filesystem.used_bytes` ([#11974](https://github.com/DataDog/integrations-core/pull/11974))

## 7.3.1 / 2022-04-11 / Agent 7.36.0

***Fixed***:

* Handle probe metrics when the endpoint is not available (Kubernetes < 1.15) ([#11807](https://github.com/DataDog/integrations-core/pull/11807))

## 7.3.0 / 2022-04-05

***Added***:

* Collect liveness and readiness probe metrics ([#11682](https://github.com/DataDog/integrations-core/pull/11682))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))
* Add pleg metrics ([#11616](https://github.com/DataDog/integrations-core/pull/11616))

***Fixed***:

* Support newer versions of `click` ([#11746](https://github.com/DataDog/integrations-core/pull/11746))
* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 7.2.1 / 2022-02-24 / Agent 7.35.0

***Fixed***:

* Apply namespace exclusion rules in cadvisor and summary metrics ([#11559](https://github.com/DataDog/integrations-core/pull/11559))

## 7.2.0 / 2022-02-19

***Added***:

* Add `pyproject.toml` file ([#11386](https://github.com/DataDog/integrations-core/pull/11386))
* Update example config ([#11515](https://github.com/DataDog/integrations-core/pull/11515))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))
* Apply namespace exclusion rules for volume metrics ([#11512](https://github.com/DataDog/integrations-core/pull/11512))

## 7.1.1 / 2022-01-08 / Agent 7.34.0

***Fixed***:

* Do not drop the first kubelet eviction event ([#11032](https://github.com/DataDog/integrations-core/pull/11032))

## 7.1.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))

***Fixed***:

* Apply namespace exclusion rules before reporting network metrics ([#10237](https://github.com/DataDog/integrations-core/pull/10237))
* Bump base package dependency ([#10218](https://github.com/DataDog/integrations-core/pull/10218))
* Don't call the tagger for pods not running ([#10030](https://github.com/DataDog/integrations-core/pull/10030))

## 7.0.0 / 2021-05-28 / Agent 7.29.0

***Changed***:

* Increase default scraping time from 15s to 20s ([#9193](https://github.com/DataDog/integrations-core/pull/9193))

## 6.1.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Allow configurability of the ignore_metrics option ([#9161](https://github.com/DataDog/integrations-core/pull/9161))

## 6.0.0 / 2021-04-14

***Changed***:

* Refactor kubelet and eks_fargate checks to use `KubeletBase` ([#8798](https://github.com/DataDog/integrations-core/pull/8798))

***Added***:

* Add logic to enable/disable metrics collected from the summary endpoint ([#9155](https://github.com/DataDog/integrations-core/pull/9155))

## 5.2.0 / 2021-03-07 / Agent 7.27.0

***Added***:

* Add new metrics ([#8562](https://github.com/DataDog/integrations-core/pull/8562))

***Fixed***:

* Fix TypeError when retrieved pod_list is occasionally None ([#8530](https://github.com/DataDog/integrations-core/pull/8530))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 5.1.0 / 2021-01-25 / Agent 7.26.0

***Added***:

* Add new default for newly autodiscovered checks ([#8177](https://github.com/DataDog/integrations-core/pull/8177))

## 5.0.0 / 2020-09-21 / Agent 7.23.0

***Changed***:

* Replace InsecureRequestWarning with standard logs ([#7512](https://github.com/DataDog/integrations-core/pull/7512))
* Improve the kubelet check error reporting in the output of `agent status` ([#7495](https://github.com/DataDog/integrations-core/pull/7495))

***Fixed***:

* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 4.1.1 / 2020-06-29 / Agent 7.21.0

***Fixed***:

* Fix missing metrics for static pods ([#6736](https://github.com/DataDog/integrations-core/pull/6736))

## 4.1.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))
* Add parsing from `/stats/summary` for Windows ([#6497](https://github.com/DataDog/integrations-core/pull/6497))
* Expose number of cfs enforcement periods ([#6093](https://github.com/DataDog/integrations-core/pull/6093)) Thanks [adammw](https://github.com/adammw).

## 4.0.0 / 2020-04-04 / Agent 7.19.0

***Changed***:

* Pass namespace to `is_excluded` ([#6217](https://github.com/DataDog/integrations-core/pull/6217))

***Fixed***:

* Update prometheus_client ([#6200](https://github.com/DataDog/integrations-core/pull/6200))
* Fix support for kubernetes v1.18 ([#6203](https://github.com/DataDog/integrations-core/pull/6203))
* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))

## 3.6.0 / 2020-02-22 / Agent 7.18.0

***Added***:

* Add pod tags to volume metrics ([#5453](https://github.com/DataDog/integrations-core/pull/5453))

## 3.5.2 / 2020-01-31 / Agent 7.17.1

***Fixed***:

* Ignore insecure warnings for kubelet requests ([#5607](https://github.com/DataDog/integrations-core/pull/5607))

## 3.5.1 / 2020-01-15 / Agent 7.17.0

***Fixed***:

* Fix Kubelet credentials handling ([#5455](https://github.com/DataDog/integrations-core/pull/5455))

## 3.5.0 / 2020-01-13

***Added***:

* Make OpenMetrics use the RequestsWrapper ([#5414](https://github.com/DataDog/integrations-core/pull/5414))
* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))
* Add log filesystem container metric ([#5383](https://github.com/DataDog/integrations-core/pull/5383))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))
* Add kubelet and runtime cpu and mem metrics ([#5370](https://github.com/DataDog/integrations-core/pull/5370))
* Update metrics for >= 1.14 ([#5336](https://github.com/DataDog/integrations-core/pull/5336))

***Fixed***:

* Improve url join to not mutate the base url when proxying a call ([#5416](https://github.com/DataDog/integrations-core/pull/5416))

## 3.4.0 / 2019-12-02 / Agent 7.16.0

***Added***:

* Collect a new metric: kubelet.evictions ([#5076](https://github.com/DataDog/integrations-core/pull/5076))
* Add a gauge for effective usage of ephemeral storage per POD ([#5052](https://github.com/DataDog/integrations-core/pull/5052))

## 3.3.4 / 2019-10-30 / Agent 6.15.0

***Fixed***:

* Fix container collection for k8s 1.16 ([#4925](https://github.com/DataDog/integrations-core/pull/4925))

## 3.3.3 / 2019-10-11

***Fixed***:

* Send kubelet metrics with tags only ([#4659](https://github.com/DataDog/integrations-core/pull/4659))

## 3.3.2 / 2019-08-14 / Agent 6.14.0

***Fixed***:

* Enforce unicode output in requests.iter_lines call ([#4360](https://github.com/DataDog/integrations-core/pull/4360))

## 3.3.1 / 2019-07-16 / Agent 6.13.0

***Fixed***:

* Update tagger usage to match prefix update ([#4109](https://github.com/DataDog/integrations-core/pull/4109))

## 3.3.0 / 2019-07-04

***Added***:

* Add swap memory checks to cadvisor kubelet checks ([#3808](https://github.com/DataDog/integrations-core/pull/3808)) Thanks [adammw](https://github.com/adammw).

## 3.2.1 / 2019-06-28 / Agent 6.12.1

***Fixed***:

* Make the kubelet and ECS fargate checks resilient to the tagger returning None ([#4004](https://github.com/DataDog/integrations-core/pull/4004))

## 3.2.0 / 2019-06-13 / Agent 6.12.0

***Fixed***:

* Revert "Collect network usage metrics (#3740)" ([#3914](https://github.com/DataDog/integrations-core/pull/3914))

## 3.1.0 / 2019-05-14

***Added***:

* Collect network usage metrics ([#3740](https://github.com/DataDog/integrations-core/pull/3740))
* add useful prometheus labels to metric tags ([#3735](https://github.com/DataDog/integrations-core/pull/3735))
* Adhere to code style ([#3525](https://github.com/DataDog/integrations-core/pull/3525))

## 3.0.1 / 2019-04-04 / Agent 6.11.0

***Fixed***:

* Fix podlist multiple iterations when using pod expiration ([#3456](https://github.com/DataDog/integrations-core/pull/3456))
* Fix health check during first check run ([#3457](https://github.com/DataDog/integrations-core/pull/3457))

## 3.0.0 / 2019-03-29

***Changed***:

* Do not tag container restarts/state metrics by container_id anymore ([#3424](https://github.com/DataDog/integrations-core/pull/3424))

***Added***:

* Allow to filter out old pods when parsing the podlist to reduce memory usage ([#3189](https://github.com/DataDog/integrations-core/pull/3189))

## 2.4.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Support Python 3 ([#3028](https://github.com/DataDog/integrations-core/pull/3028))

***Fixed***:

* Fix usage metrics collection for static pods ([#3079](https://github.com/DataDog/integrations-core/pull/3079))
* Resolve flake8 issues ([#3060](https://github.com/DataDog/integrations-core/pull/3060))
* Fix pods/container.running metrics to exclude non running ones ([#3025](https://github.com/DataDog/integrations-core/pull/3025))

## 2.3.1 / 2019-01-04 / Agent 6.9.0

***Fixed***:

* document kubernetes.pods.running and kubernetes.containers.running ([#2792][1])
* Fix default yaml instance ([#2756][2])
* Make the check robust to an unresponsive kubelet ([#2719][3])

## 2.3.0 / 2018-11-30 / Agent 6.8.0

***Added***:

* Add restart and container state metrics to kubelet ([#2605][4]) Thanks [schleyfox][5].
* Add more cpu metrics ([#2595][6])
* Add kubelet volume metrics ([#2256][7]) Thanks [derekchan][8].

***Fixed***:

* [kubelet] correctly ignore pods that are neither running or pending for resource limits&requests ([#2597][9])

## 2.2.0 / 2018-10-12 / Agent 6.6.0

***Added***:

* Add kubelet rss and working set memory metrics ([#2390][10])

## 2.1.0 / 2018-10-10

***Added***:

* Add additional kubelet metrics ([#2245][14])
* Add the kubernetes.containers.running metric ([#2191][15]) Thanks [Devatoria][16].

***Fixed***:

* Fix parsing errors when the podlist is in an inconsistent state ([#2338][11])
* Fix kubelet input filtering ([#2344][12])
* Fix pod metric filtering for containerd ([#2283][13])

## 2.0.0 / 2018-09-04 / Agent 6.5.0

***Changed***:

* Update kubelet to use the new OpenMetricsBaseCheck ([#1982][17])
* Get pod & container IDs from the pod list for reliability ([#1996][19])

***Added***:

* Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default ([#2093][18])

***Fixed***:

* Fixing typo in the pod list path used in the kubelet integration  ([#1847][20])
* Fix network and disk metric collection when multiple devices are used by a container ([#1894][21])
* Improve check performance by filtering it's input before parsing ([#1875][22])
* Reduce log spam on kubernetes tagging ([#1830][23])
* Add data files to the wheel package ([#1727][24])

## 1.4.0 / 2018-06-14 / Agent 6.3.1

***Changed***:

* Kubelet check: better encapsulate the pod list retrieval ([#1648][25])

## 1.3.0 / 2018-06-07

***Added***:

* Support for gathering metrics from prometheus endpoint for the kubelet itself. ([#1581][26])

## 1.2.0 / 2018-05-11

***Added***:

* Collect metrics directly from cadvisor, for kubenetes version older than 1.7.6. See [#1339][27]
* Add instance tags to all metrics. Improve the coverage of the check. See [#1377][28]
* Allow to disable prometheus metric collection. See [#1423][30]
* Container metrics now respect the container filtering rules. Requires Agent 6.2+. See [#1442][31]

***Fixed***:

* Reports nanocores instead of cores. See [#1361][29]
* Fix submission of CPU metrics on multi-threaded containers. See [#1489][32]
* Fix SSL when specifying certificate files

## 1.1.0 / 2018-03-23

***Added***:

* Support TLS

## 1.0.0 / 2018-02-28

***Added***:

* add kubelet integration.

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

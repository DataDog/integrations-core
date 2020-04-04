# CHANGELOG - kubernetes_state

## 5.3.0 / 2020-04-04

* [Added] Allow automatic joins to all kube_{object}_labels in KSM check. See [#5650](https://github.com/DataDog/integrations-core/pull/5650).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Do not fail on octet stream content type for OpenMetrics. See [#5843](https://github.com/DataDog/integrations-core/pull/5843).

## 5.2.1 / 2020-02-27

* [Fixed] Fix type error. See [#5904](https://github.com/DataDog/integrations-core/pull/5904).

## 5.2.0 / 2020-02-22

* [Added] Add an option to enable KSM experimental metrics and add some new metrics from KSM 1.9. See [#5447](https://github.com/DataDog/integrations-core/pull/5447).
* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).

## 5.1.0 / 2020-01-13

* [Fixed] Fix logger method bug. See [#5395](https://github.com/DataDog/integrations-core/pull/5395).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 5.0.0 / 2019-12-02

* [Changed] Improves tagging compliancy. See [#5105](https://github.com/DataDog/integrations-core/pull/5105).
* [Fixed] Fix job metrics. See [#4943](https://github.com/DataDog/integrations-core/pull/4943).

## 4.7.1 / 2019-08-26

* [Fixed] Properly ignore `kube_pod_created` and `kube_pod_container_info`. See [#4435](https://github.com/DataDog/integrations-core/pull/4435).

## 4.7.0 / 2019-08-24

* [Added] Grab kube_node_info as kubernetes_state.node.count. See [#4383](https://github.com/DataDog/integrations-core/pull/4383). Thanks [therc](https://github.com/therc).
* [Added] Add VPA metrics to kubernetes_state integration. See [#4353](https://github.com/DataDog/integrations-core/pull/4353). Thanks [dturn](https://github.com/dturn).
* [Fixed] Fix job metrics. See [#4224](https://github.com/DataDog/integrations-core/pull/4224).

## 4.6.1 / 2019-07-19

* [Fixed] Fix openmetrics mixins telemetry metrics. See [#4155](https://github.com/DataDog/integrations-core/pull/4155).

## 4.6.0 / 2019-07-19

* [Fixed] Fix kubernetes_state avoid tags collision. See [#4149](https://github.com/DataDog/integrations-core/pull/4149).
* [Added] Add telemetry metrics counter by ksm collector. See [#4125](https://github.com/DataDog/integrations-core/pull/4125).

## 4.5.0 / 2019-07-13

* [Added] Telemetry check's metrics. See [#4025](https://github.com/DataDog/integrations-core/pull/4025).

## 4.4.1 / 2019-06-19

* [Fixed] Correct service check for ksm - cronjob. See [#3937](https://github.com/DataDog/integrations-core/pull/3937).

## 4.4.0 / 2019-05-14

* [Added] Adhere to code style. See [#3526](https://github.com/DataDog/integrations-core/pull/3526).

## 4.3.0 / 2019-03-29

* [Added] Upgrade protobuf to 3.7.0. See [#3272](https://github.com/DataDog/integrations-core/pull/3272).

## 4.2.0 / 2019-02-18

* [Added] Collect .hpa.condition gauges. See [#3107](https://github.com/DataDog/integrations-core/pull/3107).
* [Added] Collect PodDisruptionBudget metrics. See [#3111](https://github.com/DataDog/integrations-core/pull/3111).
* [Added] Added .daemonset.updated gauge to track daemonset updates. See [#3102](https://github.com/DataDog/integrations-core/pull/3102).
* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).
* [Added] Support Python 3. See [#3030](https://github.com/DataDog/integrations-core/pull/3030).

## 4.1.0 / 2018-12-02

* [Added] Add phase tag to pod metrics. See [#2624][1].

## 4.0.0 / 2018-11-30

* [Removed] Remove KSM deprecated pod phase service checks. See [#2631][2].
* [Fixed] Use raw string literals when \ is present. See [#2465][3].

## 3.1.0 / 2018-10-12

* [Fixed] Fix job metrics tagging on KSM 1.4+. See [#2384][4].
* [Fixed] include node condition value in check message. See [#2362][5]. Thanks [dwradcliffe][6].
* [Fixed] Fix hostname override and type for status_report.count metrics. See [#2372][7].
* [Deprecated] [kubernetes_state] don't send pod phase service checks by default. See [#2354][8].
* [Added] Report number of services per namespace and type. See [#2247][9].
* [Fixed] Fix KSM deprecation warning on A5. See [#2317][10].
* [Fixed] Include ContainerCreating in pod waiting status reasons. See [#2063][11]. Thanks [deiwin][12].

## 3.0.0 / 2018-09-04

* [Changed] Update kubernetes_state to use the new OpenMetricsBaseCheck. See [#1983][13].
* [Added] Add cluster-name suffix to node-names in kubernetes state. See [#2069][14].
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][15].
* [Added] Add `pod:` tags to kubernetes_state status reason metrics. See [#1884][16].
* [Deprecated] Deprecate sending pod phase service checks. See [#2029][17].
* [Added] Add kubernetes persistentvolume metrics. See [#1932][18]. Thanks [Devatoria][19].
* [Added] Map kube_endpoint metrics. See [#2001][20]. Thanks [mariuscoto][21].
* [Fixed] Lower case reasons before matching container.status_report.count.* metrics. See [#1949][22].
* [Fixed] Submit k_state.nodes.by_condition as gauge instead of counter. See [#1840][23].
* [Changed] Add sister gauge metrics to kubernetes_state pod service checks. See [#1578][24]. Thanks [mwhittington21][25].
* [Changed] kubernetes_state: plumb more container waiting reasons. See [#1763][26]. Thanks [stevvooe][27].
* [Added] Make HTTP request timeout configurable in prometheus checks. See [#1790][28].

## 2.7.0 / 2018-06-26

* [Added] Add an option to disable hostname override. See [#1800][29].
* [Changed] Add data files to the wheel package. See [#1727][30].

## 2.6.0 / 2018-06-13

* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664][31].

## 2.5.0 / 2018-05-11

* [BUGFIX] [Fix the chosen port][32] in recent KSM versions exposing multiple ports
* [FEATURE] Add custom tag support.

## 2.4.0 / 2018-03-23

* [IMPROVEMENT] Add kubernetes_state.nodes.by_condition count metric [#1277][33]

## 2.3.0 / 2018-02-28

* [BUGFIX] Fix fetching kubernetes_state.container.restarts with kube-state-metrics v1.2.0 [#1137][34]
* [BUGFIX] Fix rows with mismatch columns in metadata.csv [#1195][35]

## 2.2.0 / 2018-02-13

* [IMPROVEMENT] Add option in yaml to configure which label from KSM metrics to join over [#1040][36]
* [IMPROVEMENT] Add the node label wherever the pod label is present [#1000][37]
* [IMPROVEMENT] Override hostname with the node label if present [#1000][37]

## 2.0.0 / 2018-01-10

* [IMPROVEMENT] Merge kubernetes-state pod.phase.[running|succeeded|pending|failed|unknown] service checks into one actionnable service check. Will be introduced in 5.20 and will change the behavior of the service check. [#874][38]
* [IMPROVEMENT] Adding statefulset metrics. [#936][39]
* [IMPROVEMENT] Bumping protobuf to version 3.5.1. See [#965][40]

## 1.4.0 / 2017-11-21

* [UPDATE] Update auto_conf template to support agent 6 and 5.20+. See [#860][41]
* [FEATURE] Adding HPA metrics. See [#801][42]
* [FEATURE] Add metrics for GPU, PVC, CronJobs and other added in kubernetes_state 1.1.0. See [#853][43]

## 1.3.0 / 2017-08-28

* [FEATURE] Support for StatefulSet metrics. See [#561][44]
* [FEATURE] Support tag renaming via the labels_mapper option. See [#651][45]
* [FEATURE] Add basic Job metrics. See [#686][46] and [#696][47]

## 1.2.0 / 2017-07-18

* [FEATURE] Port to PrometheusCheck class and support for new 0.5.0 metrics

## 1.1.0 / 2017-06-05

* [FEATURE] Support more metrics from kube-state-metrics. See [dd-agent-3309][48], [dd-agent-3352][49] and [#343][50]

## 1.0.0 / 2017-02-23

* [FEATURE] adds Kubernetes State integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2624
[2]: https://github.com/DataDog/integrations-core/pull/2631
[3]: https://github.com/DataDog/integrations-core/pull/2465
[4]: https://github.com/DataDog/integrations-core/pull/2384
[5]: https://github.com/DataDog/integrations-core/pull/2362
[6]: https://github.com/dwradcliffe
[7]: https://github.com/DataDog/integrations-core/pull/2372
[8]: https://github.com/DataDog/integrations-core/pull/2354
[9]: https://github.com/DataDog/integrations-core/pull/2247
[10]: https://github.com/DataDog/integrations-core/pull/2317
[11]: https://github.com/DataDog/integrations-core/pull/2063
[12]: https://github.com/deiwin
[13]: https://github.com/DataDog/integrations-core/pull/1983
[14]: https://github.com/DataDog/integrations-core/pull/2069
[15]: https://github.com/DataDog/integrations-core/pull/2093
[16]: https://github.com/DataDog/integrations-core/pull/1884
[17]: https://github.com/DataDog/integrations-core/pull/2029
[18]: https://github.com/DataDog/integrations-core/pull/1932
[19]: https://github.com/Devatoria
[20]: https://github.com/DataDog/integrations-core/pull/2001
[21]: https://github.com/mariuscoto
[22]: https://github.com/DataDog/integrations-core/pull/1949
[23]: https://github.com/DataDog/integrations-core/pull/1840
[24]: https://github.com/DataDog/integrations-core/pull/1578
[25]: https://github.com/mwhittington21
[26]: https://github.com/DataDog/integrations-core/pull/1763
[27]: https://github.com/stevvooe
[28]: https://github.com/DataDog/integrations-core/pull/1790
[29]: https://github.com/DataDog/integrations-core/pull/1800
[30]: https://github.com/DataDog/integrations-core/pull/1727
[31]: https://github.com/DataDog/integrations-core/pull/1664
[32]: https://github.com/DataDog/datadog-agent/issues/1523
[33]: https://github.com/DataDog/integrations-core/pull/1277
[34]: https://github.com/DataDog/integrations-core/issues/1137
[35]: https://github.com/DataDog/integrations-core/issues/1195
[36]: https://github.com/DataDog/integrations-core/issues/1040
[37]: https://github.com/DataDog/integrations-core/issues/1000
[38]: https://github.com/DataDog/integrations-core/issues/874
[39]: https://github.com/DataDog/integrations-core/issues/936
[40]: https://github.com/DataDog/integrations-core/issues/965
[41]: https://github.com/DataDog/integrations-core/issues/860
[42]: https://github.com/DataDog/integrations-core/issues/801
[43]: https://github.com/DataDog/integrations-core/issues/853
[44]: https://github.com/DataDog/integrations-core/issues/561
[45]: https://github.com/DataDog/integrations-core/issues/651
[46]: https://github.com/DataDog/integrations-core/issues/686
[47]: https://github.com/DataDog/integrations-core/issues/696
[48]: https://github.com/DataDog/dd-agent/pull/3309
[49]: https://github.com/DataDog/dd-agent/pull/3352
[50]: https://github.com/DataDog/integrations-core/issues/343

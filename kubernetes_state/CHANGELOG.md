# CHANGELOG - kubernetes_state

## 7.4.2 / 2022-12-09 / Agent 7.42.0

* [Fixed] Update protobuf. See [#13262](https://github.com/DataDog/integrations-core/pull/13262).

## 7.4.1 / 2022-11-08 / Agent 7.41.0

* [Fixed] Bump protobuf version to 3.20.2. See [#13271](https://github.com/DataDog/integrations-core/pull/13271).

## 7.4.0 / 2022-10-28

* [Added] Add documentation for `kubernetes_state_core` core check. See [#12552](https://github.com/DataDog/integrations-core/pull/12552).

## 7.3.1 / 2022-11-07 / Agent 7.40.1

* [Fixed] Bump protobuf version to 3.20.2. See [#13269](https://github.com/DataDog/integrations-core/pull/13269).

## 7.3.0 / 2022-09-16 / Agent 7.40.0

* [Added] Update HTTP config spec templates. See [#12890](https://github.com/DataDog/integrations-core/pull/12890).
* [Added] Add `CreateContainerError` and `InvalidImageName` to waiting reasons. See [#12758](https://github.com/DataDog/integrations-core/pull/12758).

## 7.2.1 / 2022-08-05 / Agent 7.39.0

* [Fixed] Dependency updates. See [#12653](https://github.com/DataDog/integrations-core/pull/12653).

## 7.2.0 / 2022-05-15 / Agent 7.37.0

* [Added] Support dynamic bearer tokens (Bound Service Account Token Volume). See [#11915](https://github.com/DataDog/integrations-core/pull/11915).
* [Fixed] Upgrade dependencies. See [#11958](https://github.com/DataDog/integrations-core/pull/11958).

## 7.1.0 / 2022-04-05 / Agent 7.36.0

* [Added] Upgrade dependencies. See [#11726](https://github.com/DataDog/integrations-core/pull/11726).
* [Added] Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).
* [Added] Add `kube_cronjob` tag to job metrics when applicable. See [#11692](https://github.com/DataDog/integrations-core/pull/11692).
* [Fixed] Add `kube_namespace` tag to object count metrics. See [#11734](https://github.com/DataDog/integrations-core/pull/11734).
* [Fixed] Remove outdated warning in the description for the `tls_ignore_warning` option. See [#11591](https://github.com/DataDog/integrations-core/pull/11591).

## 7.0.0 / 2022-02-19 / Agent 7.35.0

* [Added] Add `pyproject.toml` file. See [#11387](https://github.com/DataDog/integrations-core/pull/11387).
* [Added] Update example config. See [#11515](https://github.com/DataDog/integrations-core/pull/11515).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).
* [Changed] Remap value 'unknown' to 'warning' for KSM 'node.ready' service check. See [#11132](https://github.com/DataDog/integrations-core/pull/11132).

## 6.0.1 / 2021-11-13 / Agent 7.33.0

* [Fixed] Fix clustername for invalid RFC1123 cases. See [#10262](https://github.com/DataDog/integrations-core/pull/10262).

## 6.0.0 / 2021-08-22 / Agent 7.31.0

* [Added] Add `kubernetes_state.statefulset.count` metric. See [#9813](https://github.com/DataDog/integrations-core/pull/9813).
* [Fixed] [ksm] Fix statefulset tag. See [#9832](https://github.com/DataDog/integrations-core/pull/9832).
* [Fixed] Add kube_job tag to job metrics. See [#9775](https://github.com/DataDog/integrations-core/pull/9775).
* [Changed] Remove messages for integrations for OK service checks. See [#9888](https://github.com/DataDog/integrations-core/pull/9888).

## 5.7.1 / 2021-06-03 / Agent 7.29.0

* [Fixed] Fix `node.by_condition` metric. See [#9467](https://github.com/DataDog/integrations-core/pull/9467).

## 5.7.0 / 2021-05-28

* [Added] KSM: add `node.by_condition` to have the conditions of individual nodes. See [#9311](https://github.com/DataDog/integrations-core/pull/9311).
* [Added] Update `auto_conf.yaml` with valid example configuration. See [#7414](https://github.com/DataDog/integrations-core/pull/7414). Thanks [jfmyers9](https://github.com/jfmyers9).

## 5.6.4 / 2021-03-07 / Agent 7.27.0

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 5.6.3 / 2020-12-23 / Agent 7.25.0

* [Fixed] Fix deployment count metric. See [#8247](https://github.com/DataDog/integrations-core/pull/8247).

## 5.6.2 / 2020-12-21

* [Fixed] Fix deployment count metric. See [#8229](https://github.com/DataDog/integrations-core/pull/8229).

## 5.6.1 / 2020-12-18

* [Fixed] [orchestrator] change cardinality of deployment count. See [#8222](https://github.com/DataDog/integrations-core/pull/8222).

## 5.6.0 / 2020-10-31 / Agent 7.24.0

* [Added] add labels from `self.SAMPLE_LABELS` to container status metrics. See [#7602](https://github.com/DataDog/integrations-core/pull/7602). Thanks [jfmyers9](https://github.com/jfmyers9).

## 5.5.1 / 2020-09-21 / Agent 7.23.0

* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 5.5.0 / 2020-06-29 / Agent 7.21.0

* [Added] Refactor to use Agent 6+ signature. See [#6906](https://github.com/DataDog/integrations-core/pull/6906).
* [Fixed] Fix debug log line for job metrics. See [#6700](https://github.com/DataDog/integrations-core/pull/6700).
* [Fixed] Fix issue when the storage class of a persistent volume is empty and add test. See [#6615](https://github.com/DataDog/integrations-core/pull/6615).

## 5.4.1 / 2020-05-21 / Agent 7.20.0

* [Fixed] Document join_standard_tags setting in conf.example.yaml. See [#6707](https://github.com/DataDog/integrations-core/pull/6707).

## 5.4.0 / 2020-05-17

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Introduce join_standard_tags setting. See [#6253](https://github.com/DataDog/integrations-core/pull/6253).
* [Fixed] Remove use of `label_to_match` to prevent deprecation warnings. See [#6503](https://github.com/DataDog/integrations-core/pull/6503).

## 5.3.0 / 2020-04-04 / Agent 7.19.0

* [Added] Allow automatic joins to all kube_{object}_labels in KSM check. See [#5650](https://github.com/DataDog/integrations-core/pull/5650).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Do not fail on octet stream content type for OpenMetrics. See [#5843](https://github.com/DataDog/integrations-core/pull/5843).

## 5.2.1 / 2020-02-27 / Agent 7.18.0

* [Fixed] Fix type error. See [#5904](https://github.com/DataDog/integrations-core/pull/5904).

## 5.2.0 / 2020-02-22

* [Added] Add an option to enable KSM experimental metrics and add some new metrics from KSM 1.9. See [#5447](https://github.com/DataDog/integrations-core/pull/5447).
* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).

## 5.1.0 / 2020-01-13 / Agent 7.17.0

* [Fixed] Fix logger method bug. See [#5395](https://github.com/DataDog/integrations-core/pull/5395).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 5.0.0 / 2019-12-02 / Agent 7.16.0

* [Changed] Improves tagging compliancy. See [#5105](https://github.com/DataDog/integrations-core/pull/5105).
* [Fixed] Fix job metrics. See [#4943](https://github.com/DataDog/integrations-core/pull/4943).

## 4.7.1 / 2019-08-26 / Agent 6.14.0

* [Fixed] Properly ignore `kube_pod_created` and `kube_pod_container_info`. See [#4435](https://github.com/DataDog/integrations-core/pull/4435).

## 4.7.0 / 2019-08-24

* [Added] Grab kube_node_info as kubernetes_state.node.count. See [#4383](https://github.com/DataDog/integrations-core/pull/4383). Thanks [therc](https://github.com/therc).
* [Added] Add VPA metrics to kubernetes_state integration. See [#4353](https://github.com/DataDog/integrations-core/pull/4353). Thanks [dturn](https://github.com/dturn).
* [Fixed] Fix job metrics. See [#4224](https://github.com/DataDog/integrations-core/pull/4224).

## 4.6.1 / 2019-07-19 / Agent 6.13.0

* [Fixed] Fix openmetrics mixins telemetry metrics. See [#4155](https://github.com/DataDog/integrations-core/pull/4155).

## 4.6.0 / 2019-07-19

* [Fixed] Fix kubernetes_state avoid tags collision. See [#4149](https://github.com/DataDog/integrations-core/pull/4149).
* [Added] Add telemetry metrics counter by ksm collector. See [#4125](https://github.com/DataDog/integrations-core/pull/4125).

## 4.5.0 / 2019-07-13

* [Added] Telemetry check's metrics. See [#4025](https://github.com/DataDog/integrations-core/pull/4025).

## 4.4.1 / 2019-06-19

* [Fixed] Correct service check for ksm - cronjob. See [#3937](https://github.com/DataDog/integrations-core/pull/3937).

## 4.4.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3526](https://github.com/DataDog/integrations-core/pull/3526).

## 4.3.0 / 2019-03-29 / Agent 6.11.0

* [Added] Upgrade protobuf to 3.7.0. See [#3272](https://github.com/DataDog/integrations-core/pull/3272).

## 4.2.0 / 2019-02-18 / Agent 6.10.0

* [Added] Collect .hpa.condition gauges. See [#3107](https://github.com/DataDog/integrations-core/pull/3107).
* [Added] Collect PodDisruptionBudget metrics. See [#3111](https://github.com/DataDog/integrations-core/pull/3111).
* [Added] Added .daemonset.updated gauge to track daemonset updates. See [#3102](https://github.com/DataDog/integrations-core/pull/3102).
* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).
* [Added] Support Python 3. See [#3030](https://github.com/DataDog/integrations-core/pull/3030).

## 4.1.0 / 2018-12-02 / Agent 6.8.0

* [Added] Add phase tag to pod metrics. See [#2624](https://github.com/DataDog/integrations-core/pull/2624).

## 4.0.0 / 2018-11-30

* [Removed] Remove KSM deprecated pod phase service checks. See [#2631](https://github.com/DataDog/integrations-core/pull/2631).
* [Fixed] Use raw string literals when \ is present. See [#2465](https://github.com/DataDog/integrations-core/pull/2465).

## 3.1.0 / 2018-10-12 / Agent 6.6.0

* [Fixed] Fix job metrics tagging on KSM 1.4+. See [#2384](https://github.com/DataDog/integrations-core/pull/2384).
* [Fixed] include node condition value in check message. See [#2362](https://github.com/DataDog/integrations-core/pull/2362). Thanks [dwradcliffe](https://github.com/dwradcliffe).
* [Fixed] Fix hostname override and type for status_report.count metrics. See [#2372](https://github.com/DataDog/integrations-core/pull/2372).
* [Deprecated] [kubernetes_state] don't send pod phase service checks by default. See [#2354](https://github.com/DataDog/integrations-core/pull/2354).
* [Added] Report number of services per namespace and type. See [#2247](https://github.com/DataDog/integrations-core/pull/2247).
* [Fixed] Fix KSM deprecation warning on A5. See [#2317](https://github.com/DataDog/integrations-core/pull/2317).
* [Fixed] Include ContainerCreating in pod waiting status reasons. See [#2063](https://github.com/DataDog/integrations-core/pull/2063). Thanks [deiwin](https://github.com/deiwin).

## 3.0.0 / 2018-09-04 / Agent 6.5.0

* [Changed] Update kubernetes_state to use the new OpenMetricsBaseCheck. See [#1983](https://github.com/DataDog/integrations-core/pull/1983).
* [Added] Add cluster-name suffix to node-names in kubernetes state. See [#2069](https://github.com/DataDog/integrations-core/pull/2069).
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093](https://github.com/DataDog/integrations-core/pull/2093).
* [Added] Add `pod:` tags to kubernetes_state status reason metrics. See [#1884](https://github.com/DataDog/integrations-core/pull/1884).
* [Deprecated] Deprecate sending pod phase service checks. See [#2029](https://github.com/DataDog/integrations-core/pull/2029).
* [Added] Add kubernetes persistentvolume metrics. See [#1932](https://github.com/DataDog/integrations-core/pull/1932). Thanks [Devatoria](https://github.com/Devatoria).
* [Added] Map kube_endpoint metrics. See [#2001](https://github.com/DataDog/integrations-core/pull/2001). Thanks [mariuscoto](https://github.com/mariuscoto).
* [Fixed] Lower case reasons before matching container.status_report.count.* metrics. See [#1949](https://github.com/DataDog/integrations-core/pull/1949).
* [Fixed] Submit k_state.nodes.by_condition as gauge instead of counter. See [#1840](https://github.com/DataDog/integrations-core/pull/1840).
* [Changed] Add sister gauge metrics to kubernetes_state pod service checks. See [#1578](https://github.com/DataDog/integrations-core/pull/1578). Thanks [mwhittington21](https://github.com/mwhittington21).
* [Changed] kubernetes_state: plumb more container waiting reasons. See [#1763](https://github.com/DataDog/integrations-core/pull/1763). Thanks [stevvooe](https://github.com/stevvooe).
* [Added] Make HTTP request timeout configurable in prometheus checks. See [#1790](https://github.com/DataDog/integrations-core/pull/1790).

## 2.7.0 / 2018-06-26 / Agent 6.3.1

* [Added] Add an option to disable hostname override. See [#1800](https://github.com/DataDog/integrations-core/pull/1800).
* [Changed] Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).

## 2.6.0 / 2018-06-13

* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664](https://github.com/DataDog/integrations-core/pull/1664).

## 2.5.0 / 2018-05-11

* [BUGFIX] [Fix the chosen port](https://github.com/DataDog/datadog-agent/issues/1523) in recent KSM versions exposing multiple ports
* [FEATURE] Add custom tag support.

## 2.4.0 / 2018-03-23

* [IMPROVEMENT] Add kubernetes_state.nodes.by_condition count metric [#1277](https://github.com/DataDog/integrations-core/pull/1277)

## 2.3.0 / 2018-02-28

* [BUGFIX] Fix fetching kubernetes_state.container.restarts with kube-state-metrics v1.2.0 [#1137](https://github.com/DataDog/integrations-core/issues/1137)
* [BUGFIX] Fix rows with mismatch columns in metadata.csv [#1195](https://github.com/DataDog/integrations-core/issues/1195)

## 2.2.0 / 2018-02-13

* [IMPROVEMENT] Add option in yaml to configure which label from KSM metrics to join over [#1040](https://github.com/DataDog/integrations-core/issues/1040)
* [IMPROVEMENT] Add the node label wherever the pod label is present [#1000](https://github.com/DataDog/integrations-core/issues/1000)
* [IMPROVEMENT] Override hostname with the node label if present [#1000](https://github.com/DataDog/integrations-core/issues/1000)

## 2.0.0 / 2018-01-10

* [IMPROVEMENT] Merge kubernetes-state pod.phase.[running|succeeded|pending|failed|unknown] service checks into one actionnable service check. Will be introduced in 5.20 and will change the behavior of the service check. [#874](https://github.com/DataDog/integrations-core/issues/874)
* [IMPROVEMENT] Adding statefulset metrics. [#936](https://github.com/DataDog/integrations-core/issues/936)
* [IMPROVEMENT] Bumping protobuf to version 3.5.1. See [#965](https://github.com/DataDog/integrations-core/issues/965)

## 1.4.0 / 2017-11-21

* [UPDATE] Update auto_conf template to support agent 6 and 5.20+. See [#860](https://github.com/DataDog/integrations-core/issues/860)
* [FEATURE] Adding HPA metrics. See [#801](https://github.com/DataDog/integrations-core/issues/801)
* [FEATURE] Add metrics for GPU, PVC, CronJobs and other added in kubernetes_state 1.1.0. See [#853](https://github.com/DataDog/integrations-core/issues/853)

## 1.3.0 / 2017-08-28

* [FEATURE] Support for StatefulSet metrics. See [#561](https://github.com/DataDog/integrations-core/issues/561)
* [FEATURE] Support tag renaming via the labels_mapper option. See [#651](https://github.com/DataDog/integrations-core/issues/651)
* [FEATURE] Add basic Job metrics. See [#686](https://github.com/DataDog/integrations-core/issues/686) and [#696](https://github.com/DataDog/integrations-core/issues/696)

## 1.2.0 / 2017-07-18

* [FEATURE] Port to PrometheusCheck class and support for new 0.5.0 metrics

## 1.1.0 / 2017-06-05

* [FEATURE] Support more metrics from kube-state-metrics. See [dd-agent-3309](https://github.com/DataDog/dd-agent/pull/3309), [dd-agent-3352](https://github.com/DataDog/dd-agent/pull/3352) and [#343](https://github.com/DataDog/integrations-core/issues/343)

## 1.0.0 / 2017-02-23

* [FEATURE] adds Kubernetes State integration.

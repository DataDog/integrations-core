# CHANGELOG - Kube-dns

## 4.0.1 / 2023-01-20 / Agent 7.43.0

* [Fixed] Fix setting of default health URL for kube_dns, kube_proxy, kube_metrics_server health checks. See [#13571](https://github.com/DataDog/integrations-core/pull/13571).

## 4.0.0 / 2022-12-09 / Agent 7.42.0

* [Fixed] Update protobuf. See [#13262](https://github.com/DataDog/integrations-core/pull/13262).
* [Changed] Add health check to kube_* integrations. See [#10668](https://github.com/DataDog/integrations-core/pull/10668).

## 3.3.1 / 2022-11-07 / Agent 7.40.1

* [Fixed] Bump protobuf version to 3.20.2. See [#13269](https://github.com/DataDog/integrations-core/pull/13269).

## 3.3.0 / 2022-09-16 / Agent 7.40.0

* [Added] Update HTTP config spec templates. See [#12890](https://github.com/DataDog/integrations-core/pull/12890).

## 3.2.1 / 2022-08-05 / Agent 7.39.0

* [Fixed] Dependency updates. See [#12653](https://github.com/DataDog/integrations-core/pull/12653).

## 3.2.0 / 2022-05-15 / Agent 7.37.0

* [Added] Support dynamic bearer tokens (Bound Service Account Token Volume). See [#11915](https://github.com/DataDog/integrations-core/pull/11915).
* [Fixed] Upgrade dependencies. See [#11958](https://github.com/DataDog/integrations-core/pull/11958).

## 3.1.0 / 2022-04-05 / Agent 7.36.0

* [Added] Upgrade dependencies. See [#11726](https://github.com/DataDog/integrations-core/pull/11726).
* [Added] Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).
* [Fixed] Remove outdated warning in the description for the `tls_ignore_warning` option. See [#11591](https://github.com/DataDog/integrations-core/pull/11591).

## 3.0.0 / 2022-02-19 / Agent 7.35.0

* [Added] Add `pyproject.toml` file. See [#11382](https://github.com/DataDog/integrations-core/pull/11382).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).
* [Fixed] Add k8s-dns-kube-dns as default AD identifier. See [#11269](https://github.com/DataDog/integrations-core/pull/11269).
* [Changed] Add tls_protocols_allowed option documentation. See [#11251](https://github.com/DataDog/integrations-core/pull/11251).

## 2.5.1 / 2022-01-18 / Agent 7.34.0

* [Fixed] Fix the type of `bearer_token_auth`. See [#11144](https://github.com/DataDog/integrations-core/pull/11144).

## 2.5.0 / 2021-11-13 / Agent 7.33.0

* [Added] Document new include_labels option. See [#10617](https://github.com/DataDog/integrations-core/pull/10617).
* [Added] Document new use_process_start_time option. See [#10601](https://github.com/DataDog/integrations-core/pull/10601).
* [Added] Add kube_dns config spec. See [#10508](https://github.com/DataDog/integrations-core/pull/10508).

## 2.4.2 / 2021-03-07 / Agent 7.27.0

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 2.4.1 / 2020-06-29 / Agent 7.21.0

* [Fixed] Use agent 6 signature. See [#6907](https://github.com/DataDog/integrations-core/pull/6907).

## 2.4.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.3.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 2.3.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3528](https://github.com/DataDog/integrations-core/pull/3528).

## 2.2.0 / 2019-03-29 / Agent 6.11.0

* [Added] Upgrade protobuf to 3.7.0. See [#3272](https://github.com/DataDog/integrations-core/pull/3272).

## 2.1.0 / 2019-02-18 / Agent 6.10.0

* [Fixed] Fix growing CPU and memory usage. See [#3066](https://github.com/DataDog/integrations-core/pull/3066).
* [Added] Support Python 3. See [#2896](https://github.com/DataDog/integrations-core/pull/2896).

## 2.0.1 / 2018-10-12 / Agent 6.6.0

* [Fixed] Submit metrics with instance tags. See [#2299](https://github.com/DataDog/integrations-core/pull/2299).

## 2.0.0 / 2018-09-04 / Agent 6.5.0

* [Changed] Update kube_dns to use the new OpenMetricsBaseCheck. See [#1980](https://github.com/DataDog/integrations-core/pull/1980).
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093](https://github.com/DataDog/integrations-core/pull/2093).
* [Added] Make HTTP request timeout configurable in prometheus checks. See [#1790](https://github.com/DataDog/integrations-core/pull/1790).
* [Fixed] Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).

## 1.4.0 / 2018-06-13 / Agent 6.4.0

* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664](https://github.com/DataDog/integrations-core/pull/1664).

## 1.3.0 / 2018-05-11

* [IMPROVEMENT] Add metrics `kubedns.request_count.count`, `kubedns.error_count.count` and `cachemiss_count.count`, alternative metrics submitted as monotonic\_counts. See [#1341](https://github.com/DataDog/integrations-core/issues/1341)

## 1.2.0 / 2018-01-10

* [IMPROVEMENT] Bumping protobuf to version 3.5.1. See [#965](https://github.com/DataDog/integrations-core/issues/965)

## 1.1.0 / 2017-11-21

* [UPDATE] Update auto\_conf template to support agent 6 and 5.20+. See [#860](https://github.com/DataDog/integrations-core/issues/860)

## 1.0.0 / 2017-07-18

* [FEATURE] Add kube-dns integration, based on new PrometheusCheck class. See [#410](https://github.com/DataDog/integrations-core/issues/410) and [#451](https://github.com/DataDog/integrations-core/issues/451), thanks [@aerostitch](https://github.com/aerostitch)

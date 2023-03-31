# CHANGELOG - Kube Metrics Server

## 3.0.1 / 2023-01-20 / Agent 7.43.0

* [Fixed] Fix setting of default health URL for kube_dns, kube_proxy, kube_metrics_server health checks. See [#13571](https://github.com/DataDog/integrations-core/pull/13571).

## 3.0.0 / 2022-12-09 / Agent 7.42.0

* [Changed] Add health check to kube_* integrations. See [#10668](https://github.com/DataDog/integrations-core/pull/10668).

## 2.3.0 / 2022-09-16 / Agent 7.40.0

* [Added] Update HTTP config spec templates. See [#12890](https://github.com/DataDog/integrations-core/pull/12890).

## 2.2.0 / 2022-05-15 / Agent 7.37.0

* [Added] Support dynamic bearer tokens (Bound Service Account Token Volume). See [#11915](https://github.com/DataDog/integrations-core/pull/11915).

## 2.1.0 / 2022-04-05 / Agent 7.36.0

* [Added] Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).
* [Fixed] Remove outdated warning in the description for the `tls_ignore_warning` option. See [#11591](https://github.com/DataDog/integrations-core/pull/11591).

## 2.0.0 / 2022-02-19 / Agent 7.35.0

* [Added] Add `pyproject.toml` file. See [#11383](https://github.com/DataDog/integrations-core/pull/11383).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).
* [Changed] Add tls_protocols_allowed option documentation. See [#11251](https://github.com/DataDog/integrations-core/pull/11251).

## 1.4.1 / 2022-01-18 / Agent 7.34.0

* [Fixed] Fix the type of `bearer_token_auth`. See [#11144](https://github.com/DataDog/integrations-core/pull/11144).

## 1.4.0 / 2021-11-13 / Agent 7.33.0

* [Added] Document new include_labels option. See [#10617](https://github.com/DataDog/integrations-core/pull/10617).
* [Added] Document new use_process_start_time option. See [#10601](https://github.com/DataDog/integrations-core/pull/10601).
* [Added] Add kube_metrics_server config spec. See [#10509](https://github.com/DataDog/integrations-core/pull/10509).

## 1.3.0 / 2021-05-28 / Agent 7.29.0

* [Added] Support 0.4.0 metrics server renamed metric names. See [#9202](https://github.com/DataDog/integrations-core/pull/9202). Thanks [eatwithforks](https://github.com/eatwithforks).

## 1.2.1 / 2021-03-07 / Agent 7.27.0

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.2.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.1.1 / 2020-02-22 / Agent 7.18.0

* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).

## 1.1.0 / 2020-01-13 / Agent 7.17.0

* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).

## 1.0.1 / 2019-08-24 / Agent 6.14.0

* [Fixed] Fix prometheus_url conf. See [#4175](https://github.com/DataDog/integrations-core/pull/4175).

## 1.0.0 / 2019-06-01 / Agent 6.12.0

* [Added] Add Kube metrics server integration. See [#3666](https://github.com/DataDog/integrations-core/pull/3666).

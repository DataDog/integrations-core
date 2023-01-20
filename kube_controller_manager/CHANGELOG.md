# CHANGELOG - Kube_controller_manager

## 4.3.0 / 2022-09-16 / Agent 7.40.0

* [Added] Update HTTP config spec templates. See [#12890](https://github.com/DataDog/integrations-core/pull/12890).

## 4.2.0 / 2022-05-15 / Agent 7.37.0

* [Added] Support dynamic bearer tokens (Bound Service Account Token Volume). See [#11915](https://github.com/DataDog/integrations-core/pull/11915).

## 4.1.0 / 2022-04-05 / Agent 7.36.0

* [Added] Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).
* [Fixed] Remove outdated warning in the description for the `tls_ignore_warning` option. See [#11591](https://github.com/DataDog/integrations-core/pull/11591).

## 4.0.0 / 2022-02-19 / Agent 7.35.0

* [Added] Add `pyproject.toml` file. See [#11381](https://github.com/DataDog/integrations-core/pull/11381).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).
* [Changed] Add tls_protocols_allowed option documentation. See [#11251](https://github.com/DataDog/integrations-core/pull/11251).

## 3.0.1 / 2022-01-18 / Agent 7.34.0

* [Fixed] Fix the type of `bearer_token_auth`. See [#11144](https://github.com/DataDog/integrations-core/pull/11144).

## 3.0.0 / 2022-01-08

* [Added] Add kube_controller_manager config spec. See [#10505](https://github.com/DataDog/integrations-core/pull/10505).
* [Fixed] Sync configuration spec. See [#10938](https://github.com/DataDog/integrations-core/pull/10938).
* [Changed] Update the default value of the `bearer_token` parameter to send the bearer token only to secure https endpoints by default. See [#10708](https://github.com/DataDog/integrations-core/pull/10708).

## 2.0.1 / 2021-08-25 / Agent 7.31.0

* [Fixed] Correctly use SSL options for health checks. See [#9977](https://github.com/DataDog/integrations-core/pull/9977).

## 2.0.0 / 2021-08-22

* [Changed] Add service check for K8s API Server components. See [#9773](https://github.com/DataDog/integrations-core/pull/9773).

## 1.9.0 / 2021-07-12 / Agent 7.30.0

* [Added] Fix auto-discovery for latest versions on Kubernetes. See [#9575](https://github.com/DataDog/integrations-core/pull/9575).

## 1.8.0 / 2021-03-07 / Agent 7.27.0

* [Added] Add support for Kubernetes leader election based on Lease objects. See [#8535](https://github.com/DataDog/integrations-core/pull/8535).
* [Fixed] Bump minimum base package version. See [#8770](https://github.com/DataDog/integrations-core/pull/8770) and [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.7.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.6.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.6.0 / 2020-02-22 / Agent 7.18.0

* [Added] Add auto_conf.yaml files. See [#5678](https://github.com/DataDog/integrations-core/pull/5678).

## 1.5.0 / 2020-01-13 / Agent 7.17.0

* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).
* [Fixed] Fix logger method bug. See [#5395](https://github.com/DataDog/integrations-core/pull/5395).

## 1.4.0 / 2019-07-19 / Agent 6.13.0

* [Added] Add telemetry metrics counter by ksm collector. See [#4125](https://github.com/DataDog/integrations-core/pull/4125).

## 1.3.0 / 2019-07-04

* [Added] Add support for new metrics introduced in kubernetes v1.14. See [#3905](https://github.com/DataDog/integrations-core/pull/3905).

## 1.2.0 / 2019-05-14 / Agent 6.12.0

* [Fixed] Fix the list of default rate limiters. See [#3724](https://github.com/DataDog/integrations-core/pull/3724).
* [Added] Adhere to code style. See [#3527](https://github.com/DataDog/integrations-core/pull/3527).

## 1.1.0 / 2019-02-18 / Agent 6.10.0

* [Added] Track leader election status. See [#3101](https://github.com/DataDog/integrations-core/pull/3101).
* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).

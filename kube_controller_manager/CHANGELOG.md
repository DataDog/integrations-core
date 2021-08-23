# CHANGELOG - Kube_controller_manager

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

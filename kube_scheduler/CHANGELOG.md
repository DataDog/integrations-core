# CHANGELOG - Kube_scheduler

## 2.0.1 / 2021-08-25

* [Fixed] Correctly use SSL options for health checks. See [#9977](https://github.com/DataDog/integrations-core/pull/9977).

## 2.0.0 / 2021-08-22

* [Changed] Add service check for K8s API Server components. See [#9773](https://github.com/DataDog/integrations-core/pull/9773).

## 1.9.0 / 2021-07-12 / Agent 7.30.0

* [Added] Fix auto-discovery for latest versions on Kubernetes. See [#9574](https://github.com/DataDog/integrations-core/pull/9574).

## 1.8.0 / 2021-05-28 / Agent 7.29.0

* [Added] Support "ignore_tags" configuration. See [#9392](https://github.com/DataDog/integrations-core/pull/9392).

## 1.7.0 / 2021-03-07 / Agent 7.27.0

* [Added] Add support for Kubernetes leader election based on Lease objects. See [#8535](https://github.com/DataDog/integrations-core/pull/8535).
* [Fixed] Bump base package requirement. See [#8770](https://github.com/DataDog/integrations-core/pull/8770).

## 1.6.1 / 2021-01-25 / Agent 7.26.0

* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 1.6.0 / 2020-10-31 / Agent 7.24.0

* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).

## 1.5.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add kube_scheduler config spec. See [#7614](https://github.com/DataDog/integrations-core/pull/7614).

## 1.4.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.3.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.3.0 / 2020-02-22 / Agent 7.18.0

* [Added] Add auto_conf.yaml files. See [#5678](https://github.com/DataDog/integrations-core/pull/5678).
* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).

## 1.2.0 / 2020-01-13 / Agent 7.17.0

* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).
* [Fixed] Move unit conversion helpers to openmetrics mixin. See [#5364](https://github.com/DataDog/integrations-core/pull/5364).
* [Fixed] Correct conversions from microseconds to seconds. See [#5354](https://github.com/DataDog/integrations-core/pull/5354).

## 1.1.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3530](https://github.com/DataDog/integrations-core/pull/3530).

## 1.0.0 / 2019-03-29 / Agent 6.11.0

* [Added] Added kube_scheduler check. See [#3371](https://github.com/DataDog/integrations-core/pull/3371).


# CHANGELOG - nginx-ingress-controller

## 1.8.1 / 2021-01-25

* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 1.8.0 / 2020-10-31 / Agent 7.24.0

* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] fix which prometheus metric is used for reload.success to properly monitor nginx config reload errors. See [#7595](https://github.com/DataDog/integrations-core/pull/7595). Thanks [rocktavious](https://github.com/rocktavious).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).

## 1.7.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.6.0 / 2020-08-10 / Agent 7.22.0

* [Added] Support "*" wildcard in type_overrides configuration. See [#7071](https://github.com/DataDog/integrations-core/pull/7071).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.5.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 1.4.0 / 2020-06-12

* [Added] Add flag to collect subset of histogram metrics. See [#6860](https://github.com/DataDog/integrations-core/pull/6860).
* [Added] Add configuration spec. See [#6857](https://github.com/DataDog/integrations-core/pull/6857).
* [Added] Add response duration metric to nginx ingress controller check. See [#6836](https://github.com/DataDog/integrations-core/pull/6836).

## 1.3.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.2.2 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.2.1 / 2020-02-22 / Agent 7.18.0

* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).

## 1.2.0 / 2020-01-13 / Agent 7.17.0

* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).

## 1.1.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3546](https://github.com/DataDog/integrations-core/pull/3546).

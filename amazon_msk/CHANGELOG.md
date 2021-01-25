# CHANGELOG - Amazon MSK

## 1.4.1 / 2021-01-25

* [Fixed] Hide auto-populated prometheus_url from config spec. See [#8330](https://github.com/DataDog/integrations-core/pull/8330).
* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 1.4.0 / 2020-12-11 / Agent 7.25.0

* [Added] Add ability to assume a specified role when retrieving MSK metadata. See [#8118](https://github.com/DataDog/integrations-core/pull/8118). Thanks [garrett528](https://github.com/garrett528).

## 1.3.0 / 2020-10-31 / Agent 7.24.0

* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).

## 1.2.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Added] Add config specs. See [#7291](https://github.com/DataDog/integrations-core/pull/7291).

## 1.1.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.0.0 / 2019-12-03 / Agent 7.16.1

* [Added] Add Amazon MSK integration. See [#5127](https://github.com/DataDog/integrations-core/pull/5127).


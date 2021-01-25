# CHANGELOG - CoreDNS

## 1.6.1 / 2021-01-25

* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 1.6.0 / 2020-10-31 / Agent 7.24.0

* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] Add config specs. See [#7444](https://github.com/DataDog/integrations-core/pull/7444).

## 1.5.0 / 2020-07-16 / Agent 7.22.0

* [Added] Adding new metrics for version 1.7.0 of CoreDNS. See [#6973](https://github.com/DataDog/integrations-core/pull/6973).

## 1.4.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Fixed] Agent 6 signature. See [#6444](https://github.com/DataDog/integrations-core/pull/6444).

## 1.3.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Do not fail on octet stream content type for OpenMetrics. See [#5843](https://github.com/DataDog/integrations-core/pull/5843).

## 1.3.0 / 2019-10-29 / Agent 7.16.0

* [Added] Add forward metrics. See [#4850](https://github.com/DataDog/integrations-core/pull/4850). Thanks [therc](https://github.com/therc).

## 1.2.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3492](https://github.com/DataDog/integrations-core/pull/3492).

## 1.1.0 / 2018-11-30 / Agent 6.8.0

* [Added] Add panic_count_total metric to CoreDNS integration. See [#2594][1]. Thanks [woopstar][2].

## 1.0.0 / 2018-10-13 / Agent 6.6.0

* [Added] Add CoreDNS integration. See [#2091][3]. Thanks [shraykay][4].

[1]: https://github.com/DataDog/integrations-core/pull/2594
[2]: https://github.com/woopstar
[3]: https://github.com/DataDog/integrations-core/pull/2091
[4]: https://github.com/shraykay

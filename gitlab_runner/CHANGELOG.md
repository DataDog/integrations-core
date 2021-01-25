# CHANGELOG - gitlab_runner

## 2.11.1 / 2021-01-25

* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 2.11.0 / 2020-10-31 / Agent 7.24.0

* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 2.10.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add log support. See [#7455](https://github.com/DataDog/integrations-core/pull/7455).
* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Added] Add configuration spec. See [#7397](https://github.com/DataDog/integrations-core/pull/7397).

## 2.9.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 2.9.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Added] Collect version metadata. See [#6894](https://github.com/DataDog/integrations-core/pull/6894).

## 2.8.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.7.2 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 2.7.1 / 2020-02-22 / Agent 7.18.0

* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).

## 2.7.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).

## 2.6.0 / 2019-11-06 / Agent 7.16.0

* [Added] update gitlab_runner metrics. See [#4799](https://github.com/DataDog/integrations-core/pull/4799).

## 2.5.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 2.4.1 / 2019-08-30 / Agent 6.14.0

* [Fixed] Update class signature to support the RequestsWrapper. See [#4469](https://github.com/DataDog/integrations-core/pull/4469).

## 2.4.0 / 2019-08-24

* [Fixed] Update RequestsWrapper with read/connect timeout. See [#4241](https://github.com/DataDog/integrations-core/pull/4241).
* [Added] Add requests wrapper to gitlab_runner. See [#4218](https://github.com/DataDog/integrations-core/pull/4218).

## 2.3.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3510](https://github.com/DataDog/integrations-core/pull/3510).

## 2.2.0 / 2019-03-29 / Agent 6.11.0

* [Added] Upgrade protobuf to 3.7.0. See [#3272](https://github.com/DataDog/integrations-core/pull/3272).

## 2.1.0 / 2019-02-18 / Agent 6.10.0

* [Added] Support Python 3. See [#2886](https://github.com/DataDog/integrations-core/pull/2886).

## 2.0.0 / 2018-10-12 / Agent 6.6.0

* [Changed] Update gitlab_runner to use the new OpenMetricsBaseCheck. See [#1978][1].

## 1.2.0 / 2018-09-04 / Agent 6.5.0

* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][2].
* [Fixed] Add data files to the wheel package. See [#1727][3].

## 1.1.0 / 2018-03-23

* [FEATURE] Add custom tag support.

## 1.0.0 / 2018-01-10

* [FEATURE] Add integration for Gitlab Runners.
[1]: https://github.com/DataDog/integrations-core/pull/1978
[2]: https://github.com/DataDog/integrations-core/pull/2093
[3]: https://github.com/DataDog/integrations-core/pull/1727

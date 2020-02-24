# CHANGELOG - gitlab_runner

## 2.7.1 / 2020-02-22

* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).

## 2.7.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).

## 2.6.0 / 2019-11-06

* [Added] update gitlab_runner metrics. See [#4799](https://github.com/DataDog/integrations-core/pull/4799).

## 2.5.0 / 2019-10-11

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 2.4.1 / 2019-08-30

* [Fixed] Update class signature to support the RequestsWrapper. See [#4469](https://github.com/DataDog/integrations-core/pull/4469).

## 2.4.0 / 2019-08-24

* [Fixed] Update RequestsWrapper with read/connect timeout. See [#4241](https://github.com/DataDog/integrations-core/pull/4241).
* [Added] Add requests wrapper to gitlab_runner. See [#4218](https://github.com/DataDog/integrations-core/pull/4218).

## 2.3.0 / 2019-05-14

* [Added] Adhere to code style. See [#3510](https://github.com/DataDog/integrations-core/pull/3510).

## 2.2.0 / 2019-03-29

* [Added] Upgrade protobuf to 3.7.0. See [#3272](https://github.com/DataDog/integrations-core/pull/3272).

## 2.1.0 / 2019-02-18

* [Added] Support Python 3. See [#2886](https://github.com/DataDog/integrations-core/pull/2886).

## 2.0.0 / 2018-10-12

* [Changed] Update gitlab_runner to use the new OpenMetricsBaseCheck. See [#1978][1].

## 1.2.0 / 2018-09-04

* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][2].
* [Fixed] Add data files to the wheel package. See [#1727][3].

## 1.1.0 / 2018-03-23

* [FEATURE] Add custom tag support.

## 1.0.0 / 2018-01-10

* [FEATURE] Add integration for Gitlab Runners.
[1]: https://github.com/DataDog/integrations-core/pull/1978
[2]: https://github.com/DataDog/integrations-core/pull/2093
[3]: https://github.com/DataDog/integrations-core/pull/1727

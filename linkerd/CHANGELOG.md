# CHANGELOG - Linkerd

## 2.7.0 / 2021-01-25

* [Added] Allow the use of the new OpenMetrics implementation. See [#8438](https://github.com/DataDog/integrations-core/pull/8438).
* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 2.6.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add configuration spec. See [#7872](https://github.com/DataDog/integrations-core/pull/7872).

## 2.5.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.4.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 2.4.0 / 2020-01-13 / Agent 7.17.0

* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).
* [Fixed] Raise exception to report when openmetrics process fails. See [#5392](https://github.com/DataDog/integrations-core/pull/5392).

## 2.3.0 / 2019-06-24 / Agent 6.13.0

* [Added] Support v2. See [#3911](https://github.com/DataDog/integrations-core/pull/3911).

## 2.2.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3533](https://github.com/DataDog/integrations-core/pull/3533).

## 2.1.0 / 2019-02-18 / Agent 6.10.0

* [Added] Support Python 3. See [#3032](https://github.com/DataDog/integrations-core/pull/3032).

## 2.0.0 / 2018-10-12 / Agent 6.6.0

* [Changed] Update linkerd to use the new OpenMetricsBaseCheck. See [#1984][1].

## 1.2.0 / 2018-09-04 / Agent 6.5.0

* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][2].
* [Added] Make HTTP request timeout configurable in prometheus checks. See [#1790][3].
* [Fixed] Add data files to the wheel package. See [#1727][4].

## 1.1.0 / 2018-06-07

* [Added] Support for gathering metrics from prometheus endpoint for the kubelet itself.. See [#1581][5].

## 1.0.0/ 2018-03-23

* [FEATURE] adds linkerd integration.
[1]: https://github.com/DataDog/integrations-core/pull/1984
[2]: https://github.com/DataDog/integrations-core/pull/2093
[3]: https://github.com/DataDog/integrations-core/pull/1790
[4]: https://github.com/DataDog/integrations-core/pull/1727
[5]: https://github.com/DataDog/integrations-core/pull/1581

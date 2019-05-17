# CHANGELOG - Linkerd

## 2.2.0 / 2019-05-14

* [Added] Adhere to code style. See [#3533](https://github.com/DataDog/integrations-core/pull/3533).

## 2.1.0 / 2019-02-18

* [Added] Support Python 3. See [#3032](https://github.com/DataDog/integrations-core/pull/3032).

## 2.0.0 / 2018-10-12

* [Changed] Update linkerd to use the new OpenMetricsBaseCheck. See [#1984][1].

## 1.2.0 / 2018-09-04

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

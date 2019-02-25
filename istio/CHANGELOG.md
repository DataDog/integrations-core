# CHANGELOG - istio

## 2.1.0 / 2019-02-18

* [Fixed] Update example config to match docs. See [#3046](https://github.com/DataDog/integrations-core/pull/3046).
* [Added] Support Python 3. See [#3014](https://github.com/DataDog/integrations-core/pull/3014).

## 2.0.0 / 2018-09-04

* [Changed] Update istio to use the new OpenMetricsBaseCheck. See [#1979][1].
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][2].
* [Added] Update istio mapped metrics. See [#1993][3]. Thanks [bobbytables][4].
* [Fixed] Add data files to the wheel package. See [#1727][5].

## 1.1.0 / 2018-06-07

* [Added] Support for gathering metrics from prometheus endpoint for the kubelet itself.. See [#1581][6].

## 1.0.0 / 2018-03-23

* [FEATURE] Adds Istio Integration
[1]: https://github.com/DataDog/integrations-core/pull/1979
[2]: https://github.com/DataDog/integrations-core/pull/2093
[3]: https://github.com/DataDog/integrations-core/pull/1993
[4]: https://github.com/bobbytables
[5]: https://github.com/DataDog/integrations-core/pull/1727
[6]: https://github.com/DataDog/integrations-core/pull/1581

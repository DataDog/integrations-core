# CHANGELOG - Kube_proxy

## 3.3.1 / 2020-04-04

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 3.3.0 / 2020-01-13

* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).

## 3.2.0 / 2019-05-14

* [Added] Adhere to code style. See [#3529](https://github.com/DataDog/integrations-core/pull/3529).

## 3.1.0 / 2019-02-18

* [Added] Support Python 3. See [#2919](https://github.com/DataDog/integrations-core/pull/2919).

## 3.0.0 / 2018-10-12

* [Changed] Update kube_proxy to use the new OpenMetricsBaseCheck. See [#1981][1].

## 2.0.0 / 2018-09-04

* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][2].
* [Fixed] Make sure all checks' versions are exposed. See [#1945][3].
* [Added] Make HTTP request timeout configurable in prometheus checks. See [#1790][4].
* [Changed] Removing unnecessary and misleading kube_proxy auto_conf.yaml. See [#1792][5].
* [Fixed] Add data files to the wheel package. See [#1727][6].

## 1.1.0 / 2018-06-07

* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664][7].

## 1.0.0/ 2018-03-23

* [FEATURE] adds kube_proxy integration.
[1]: https://github.com/DataDog/integrations-core/pull/1981
[2]: https://github.com/DataDog/integrations-core/pull/2093
[3]: https://github.com/DataDog/integrations-core/pull/1945
[4]: https://github.com/DataDog/integrations-core/pull/1790
[5]: https://github.com/DataDog/integrations-core/pull/1792
[6]: https://github.com/DataDog/integrations-core/pull/1727
[7]: https://github.com/DataDog/integrations-core/pull/1664

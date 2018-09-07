# CHANGELOG - Kube_proxy

## 2.0.0 / 2018-09-04

* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093](https://github.com/DataDog/integrations-core/pull/2093).
* [Fixed] Make sure all checks' versions are exposed. See [#1945](https://github.com/DataDog/integrations-core/pull/1945).
* [Added] Make HTTP request timeout configurable in prometheus checks. See [#1790](https://github.com/DataDog/integrations-core/pull/1790).
* [Changed] Removing unnecessary and misleading kube_proxy auto_conf.yaml. See [#1792](https://github.com/DataDog/integrations-core/pull/1792).
* [Fixed] Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).

## 1.1.0 / 2018-06-07

* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664](https://github.com/DataDog/integrations-core/pull/1664).

## 1.0.0/ 2018-03-23

* [FEATURE] adds kube_proxy integration.

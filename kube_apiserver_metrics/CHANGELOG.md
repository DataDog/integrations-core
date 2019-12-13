# CHANGELOG - Kube_apiserver_metrics

## 1.2.1 / 2019-12-13

* [Fixed] Fix scrapper config cache issue. See [#5202](https://github.com/DataDog/integrations-core/pull/5202).

## 1.2.0 / 2019-12-02

* [Added] Handle scheme in `prometheus_url` instead of the separate `scheme` option, which is now deprecated. See [#4913](https://github.com/DataDog/integrations-core/pull/4913).

## 1.1.1 / 2019-10-16

* [Fixed] Use default port for kube apiserver metrics auto conf. See [#4785](https://github.com/DataDog/integrations-core/pull/4785).

## 1.1.0 / 2019-10-11

* [Added] Scrape apiserver_request_total metric introduced in v1.15. See [#4546](https://github.com/DataDog/integrations-core/pull/4546).

## 1.0.1 / 2019-06-06

* [Fixed] Fix default for bearer_token and ssl_verify. See [#3882](https://github.com/DataDog/integrations-core/pull/3882).

## 1.0.0 / 2019-05-31

* [Added] Introducing the Kubernetes APIServer metrics check. See [#3746](https://github.com/DataDog/integrations-core/pull/3746).

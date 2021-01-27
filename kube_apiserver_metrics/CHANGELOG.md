# CHANGELOG - Kube_apiserver_metrics

## 1.7.1 / 2021-01-25

* [Fixed] Update metrics whose name has changed in Kubernetes 1.14. See [#8337](https://github.com/DataDog/integrations-core/pull/8337).
* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 1.7.0 / 2020-10-31 / Agent 7.24.0

* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).

## 1.6.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).
* [Fixed] Use consistent formatting for boolean values. See [#7405](https://github.com/DataDog/integrations-core/pull/7405).

## 1.5.0 / 2020-08-10 / Agent 7.22.0

* [Added] Support "*" wildcard in type_overrides configuration. See [#7071](https://github.com/DataDog/integrations-core/pull/7071).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.4.1 / 2020-07-02 / Agent 7.21.0

* [Fixed] Fix default value in example configuration file. See [#7034](https://github.com/DataDog/integrations-core/pull/7034).

## 1.4.0 / 2020-06-29

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Added] kube apiserver signature and specs. See [#6831](https://github.com/DataDog/integrations-core/pull/6831).
* [Fixed] Sync example configs. See [#6920](https://github.com/DataDog/integrations-core/pull/6920).

## 1.3.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add admission controller metrics. See [#6502](https://github.com/DataDog/integrations-core/pull/6502).

## 1.2.3 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.2.2 / 2020-01-13 / Agent 7.17.0

* [Fixed] Update Kube_apiserver_metrics annotations documentation. See [#5199](https://github.com/DataDog/integrations-core/pull/5199).

## 1.2.1 / 2019-12-13 / Agent 7.16.0

* [Fixed] Fix scrapper config cache issue. See [#5202](https://github.com/DataDog/integrations-core/pull/5202).

## 1.2.0 / 2019-12-02

* [Added] Handle scheme in `prometheus_url` instead of the separate `scheme` option, which is now deprecated. See [#4913](https://github.com/DataDog/integrations-core/pull/4913).

## 1.1.1 / 2019-10-16 / Agent 6.15.0

* [Fixed] Use default port for kube apiserver metrics auto conf. See [#4785](https://github.com/DataDog/integrations-core/pull/4785).

## 1.1.0 / 2019-10-11

* [Added] Scrape apiserver_request_total metric introduced in v1.15. See [#4546](https://github.com/DataDog/integrations-core/pull/4546).

## 1.0.1 / 2019-06-06 / Agent 6.12.0

* [Fixed] Fix default for bearer_token and ssl_verify. See [#3882](https://github.com/DataDog/integrations-core/pull/3882).

## 1.0.0 / 2019-05-31

* [Added] Introducing the Kubernetes APIServer metrics check. See [#3746](https://github.com/DataDog/integrations-core/pull/3746).

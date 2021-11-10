# CHANGELOG - OpenMetrics

## 1.15.2 / 2021-10-15 / Agent 7.32.0

* [Fixed] [OpenMetricsV2] Allow empty namespaces. See [#10420](https://github.com/DataDog/integrations-core/pull/10420).

## 1.15.1 / 2021-10-08

* [Fixed] Allow entire config templates to be hidden and include Openmetrics legacy config option in models. See [#10348](https://github.com/DataDog/integrations-core/pull/10348).

## 1.15.0 / 2021-10-04

* [Added] Add runtime configuration validation. See [#8965](https://github.com/DataDog/integrations-core/pull/8965).
* [Added] Add HTTP option to control the size of streaming responses. See [#10183](https://github.com/DataDog/integrations-core/pull/10183).
* [Added] Add allow_redirect option. See [#10160](https://github.com/DataDog/integrations-core/pull/10160).
* [Added] Update documentation for v2. See [#10068](https://github.com/DataDog/integrations-core/pull/10068).
* [Fixed] Fix the description of the `allow_redirects` HTTP option. See [#10195](https://github.com/DataDog/integrations-core/pull/10195).

## 1.14.1 / 2021-08-22 / Agent 7.31.0

* [Fixed] Update `metrics` option in legacy OpenMetrics example config. See [#9891](https://github.com/DataDog/integrations-core/pull/9891).

## 1.14.0 / 2021-05-28 / Agent 7.29.0

* [Added] Support "ignore_tags" configuration. See [#9392](https://github.com/DataDog/integrations-core/pull/9392).
* [Fixed] Fix `metrics` option type for legacy OpenMetrics config spec. See [#9318](https://github.com/DataDog/integrations-core/pull/9318). Thanks [jejikenwogu](https://github.com/jejikenwogu).

## 1.13.0 / 2021-04-19 / Agent 7.28.0

* [Added] Update defaults for legacy OpenMetrics config spec template. See [#9065](https://github.com/DataDog/integrations-core/pull/9065).

## 1.12.1 / 2021-03-07 / Agent 7.27.0

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.12.0 / 2021-01-25 / Agent 7.26.0

* [Added] Allow the use of the new OpenMetrics implementation. See [#8440](https://github.com/DataDog/integrations-core/pull/8440).
* [Fixed] Update prometheus_metrics_prefix documentation. See [#8236](https://github.com/DataDog/integrations-core/pull/8236).

## 1.11.0 / 2020-10-31 / Agent 7.24.0

* [Added] Sync openmetrics config specs with new option ignore_metrics_by_labels. See [#7823](https://github.com/DataDog/integrations-core/pull/7823).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).

## 1.10.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.9.0 / 2020-08-10 / Agent 7.22.0

* [Added] Support "*" wildcard in type_overrides configuration. See [#7071](https://github.com/DataDog/integrations-core/pull/7071).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.8.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 1.7.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add default template to openmetrics & jmx config. See [#6328](https://github.com/DataDog/integrations-core/pull/6328).
* [Fixed] Hide openmetrics template options that are typically overridden. See [#6338](https://github.com/DataDog/integrations-core/pull/6338).

## 1.6.1 / 2020-04-07 / Agent 7.19.0

* [Fixed] Add `kerberos_cache` to HTTP config options. See [#6279](https://github.com/DataDog/integrations-core/pull/6279).

## 1.6.0 / 2020-04-04

* [Added] Add OpenMetrics config spec template. See [#6142](https://github.com/DataDog/integrations-core/pull/6142).
* [Added] Allow option to submit histogram/summary sum metric as monotonic count. See [#6127](https://github.com/DataDog/integrations-core/pull/6127).
* [Fixed] Sync OpenMetrics config. See [#6250](https://github.com/DataDog/integrations-core/pull/6250).
* [Fixed] Add `send_distribution_sums_as_monotonic` to openmetrics config spec. See [#6247](https://github.com/DataDog/integrations-core/pull/6247).
* [Fixed] Update prometheus_client. See [#6200](https://github.com/DataDog/integrations-core/pull/6200).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.5.0 / 2020-02-22 / Agent 7.18.0

* [Added] Make `ignore_metrics` support `*` wildcard for OpenMetrics. See [#5759](https://github.com/DataDog/integrations-core/pull/5759).

## 1.4.0 / 2020-01-13 / Agent 7.17.0

* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).

## 1.3.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add an option to send histograms/summary counts as monotonic counters. See [#4629](https://github.com/DataDog/integrations-core/pull/4629).

## 1.2.0 / 2019-06-01 / Agent 6.12.0

* [Added] Use Kube service account bearer token for authentication. See [#3829](https://github.com/DataDog/integrations-core/pull/3829).

## 1.1.0 / 2019-05-14

* [Fixed] Fix type override values in example config. See [#3717](https://github.com/DataDog/integrations-core/pull/3717).
* [Added] Adhere to code style. See [#3549](https://github.com/DataDog/integrations-core/pull/3549).

## 1.0.0 / 2018-10-13 / Agent 6.6.0

* [Added] Add OpenMetrics integration. See [#2148][1].

[1]: https://github.com/DataDog/integrations-core/pull/2148

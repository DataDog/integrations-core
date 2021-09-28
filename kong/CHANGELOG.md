# CHANGELOG - kong

## 1.15.0 / 2021-08-22 / Agent 7.31.0

* [Added] [OpenMetricsV2] Improve label sharing behavior. See [#9804](https://github.com/DataDog/integrations-core/pull/9804).

## 1.14.1 / 2021-07-12 / Agent 7.30.0

* [Fixed] Raise exception if attempting to use new style openmetrics with py2. See [#9613](https://github.com/DataDog/integrations-core/pull/9613).

## 1.14.0 / 2021-05-28 / Agent 7.29.0

* [Added] Support "ignore_tags" configuration. See [#9392](https://github.com/DataDog/integrations-core/pull/9392).
* [Added] [OpenMetricsV2] Add an option to send sum and count information when using distribution metrics. See [#9301](https://github.com/DataDog/integrations-core/pull/9301).

## 1.13.0 / 2021-04-19 / Agent 7.28.0

* [Added] Add new implementation based on the official Prometheus plugin. See [#9031](https://github.com/DataDog/integrations-core/pull/9031).
* [Fixed] Bump minimum base package. See [#9107](https://github.com/DataDog/integrations-core/pull/9107).
* [Fixed] Bump minimum base package version. See [#9096](https://github.com/DataDog/integrations-core/pull/9096).

## 1.12.1 / 2021-03-07 / Agent 7.27.0

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.12.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 1.11.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.10.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.10.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 1.9.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.8.1 / 2020-04-07 / Agent 7.19.0

* [Fixed] Add `kerberos_cache` to HTTP config options. See [#6279](https://github.com/DataDog/integrations-core/pull/6279).

## 1.8.0 / 2020-04-04

* [Added] Add option to set SNI hostname via the `Host` header for RequestsWrapper. See [#5833](https://github.com/DataDog/integrations-core/pull/5833).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.7.1 / 2020-02-25 / Agent 7.18.0

* [Fixed] Update datadog_checks_base dependencies. See [#5846](https://github.com/DataDog/integrations-core/pull/5846).

## 1.7.0 / 2020-02-22

* [Added] Add `service` option to default configuration. See [#5805](https://github.com/DataDog/integrations-core/pull/5805).
* [Added] Adds RequestsWrapper to Kong. See [#5807](https://github.com/DataDog/integrations-core/pull/5807).

## 1.6.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).

## 1.5.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3524](https://github.com/DataDog/integrations-core/pull/3524).

## 1.4.0 / 2019-03-29 / Agent 6.11.0

* [Added] Update the kong integration with log instruction. See [#2935](https://github.com/DataDog/integrations-core/pull/2935).

## 1.3.0 / 2019-01-04 / Agent 6.9.0

* [Added] Support Python 3. See [#2772][1].

## 1.2.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Add data files to the wheel package. See [#1727][2].

## 1.2.0 / 2018-05-11

* [FEATURE] Add `ssl_validation` settings to disable SSL Cert Verification

## 1.1.0 / 2018-03-23

* [FEATURE] Add custom tag support to service checks.

## 1.0.0 / 2017-03-22

* [FEATURE] adds kong integration.
[1]: https://github.com/DataDog/integrations-core/pull/2772
[2]: https://github.com/DataDog/integrations-core/pull/1727

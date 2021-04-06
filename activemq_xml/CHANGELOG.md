# CHANGELOG - activemq_xml

## 1.10.1 / 2021-03-07

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.10.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).

## 1.9.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.8.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.8.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 1.7.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.6.1 / 2020-04-07 / Agent 7.19.0

* [Fixed] Add `kerberos_cache` to HTTP config options. See [#6279](https://github.com/DataDog/integrations-core/pull/6279).

## 1.6.0 / 2020-04-04

* [Added] Add option to set SNI hostname via the `Host` header for RequestsWrapper. See [#5833](https://github.com/DataDog/integrations-core/pull/5833).
* [Added] Add config specs to activemq xml. See [#6116](https://github.com/DataDog/integrations-core/pull/6116).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.5.0 / 2019-12-02 / Agent 7.16.0

* [Added] Standardize logging format. See [#4896](https://github.com/DataDog/integrations-core/pull/4896).

## 1.4.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.3.0 / 2019-08-24 / Agent 6.14.0

* [Added] Update with proxy settings . See [#3361](https://github.com/DataDog/integrations-core/pull/3361).

## 1.2.0 / 2019-03-29 / Agent 6.11.0

* [Added] Adhere to code style. See [#3323](https://github.com/DataDog/integrations-core/pull/3323).

## 1.1.0 / 2018-11-30 / Agent 6.8.0

* [Added] Add Python3 Support. See [#2583][1].

## 1.0.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Add data files to the wheel package. See [#1727][2].

## 1.0.0 / 2017-03-22

* [FEATURE] adds activemq_xml integration.
[1]: https://github.com/DataDog/integrations-core/pull/2583
[2]: https://github.com/DataDog/integrations-core/pull/1727

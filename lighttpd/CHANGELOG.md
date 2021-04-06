# CHANGELOG - lighttpd

## 1.13.2 / 2021-03-07

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.13.1 / 2020-11-03 / Agent 7.24.0

* [Fixed] Remove default `encoding` example in logs config. See [#7916](https://github.com/DataDog/integrations-core/pull/7916).

## 1.13.0 / 2020-10-31

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] Add lighttpd logs. See [#7719](https://github.com/DataDog/integrations-core/pull/7719).

## 1.12.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.11.0 / 2020-08-10 / Agent 7.22.0

* [Added] Add config specs. See [#7057](https://github.com/DataDog/integrations-core/pull/7057).
* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.10.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).

## 1.9.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.8.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.8.0 / 2020-02-22 / Agent 7.18.0

* [Added] Add version metadata. See [#5600](https://github.com/DataDog/integrations-core/pull/5600).

## 1.7.0 / 2019-12-02 / Agent 7.16.0

* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 1.6.0 / 2019-10-11 / Agent 6.15.0

* [Fixed] Fix lighttpd logging format. See [#4716](https://github.com/DataDog/integrations-core/pull/4716).
* [Fixed] Fix support for no authentication. See [#4689](https://github.com/DataDog/integrations-core/pull/4689).
* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.5.0 / 2019-08-24 / Agent 6.14.0

* [Fixed] Update __init__ method params. See [#4243](https://github.com/DataDog/integrations-core/pull/4243).
* [Added] Add requests wrapper to lighttpd. See [#4220](https://github.com/DataDog/integrations-core/pull/4220).

## 1.4.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3532](https://github.com/DataDog/integrations-core/pull/3532).

## 1.3.0 / 2019-01-04 / Agent 6.9.0

* [Added] Support Python 3. See [#2834][1].

## 1.2.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Add data files to the wheel package. See [#1727][2].

## 1.2.0 / 2018-05-11

* [FEATURE] Support digest authentication on the server status page.

## 1.1.0 / 2018-03-23

* [FEATURE] Adds custom tag support to service checks.

## 1.0.0 / 2017-03-22

* [FEATURE] adds lighttpd integration.
[1]: https://github.com/DataDog/integrations-core/pull/2834
[2]: https://github.com/DataDog/integrations-core/pull/1727

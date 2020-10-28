# CHANGELOG - Twistlock

## 1.9.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.8.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.8.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Added] Add config specs. See [#6795](https://github.com/DataDog/integrations-core/pull/6795).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 1.7.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.6.0 / 2020-04-04 / Agent 7.19.0

* [Added] Use a faster JSON library. See [#6143](https://github.com/DataDog/integrations-core/pull/6143).

## 1.5.0 / 2020-01-13 / Agent 7.17.0

* [Added] Add Prisma Cloud compatibility. See [#5360](https://github.com/DataDog/integrations-core/pull/5360).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 1.4.1 / 2020-01-02

* [Fixed] Fix possible TypeError due to NoneType in parser.isoparse. See [#5265](https://github.com/DataDog/integrations-core/pull/5265).
* [Fixed] Fix possible KeyError in _report_compliance_information. See [#5248](https://github.com/DataDog/integrations-core/pull/5248).

## 1.4.0 / 2019-11-06 / Agent 7.16.0

* [Added] Allow passing a "project" query parameter. See [#4667](https://github.com/DataDog/integrations-core/pull/4667).

## 1.3.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.2.2 / 2019-08-30 / Agent 6.14.0

* [Fixed] Update class signature to support the RequestsWrapper. See [#4469](https://github.com/DataDog/integrations-core/pull/4469).

## 1.2.1 / 2019-08-13

* [Fixed] Fix date format matching. See [#4304](https://github.com/DataDog/integrations-core/pull/4304).

## 1.2.0 / 2019-08-02

* [Added] Add RequestsWrapper to twistlock. See [#4122](https://github.com/DataDog/integrations-core/pull/4122).
* [Fixed] Use utcnow instead of now. See [#4192](https://github.com/DataDog/integrations-core/pull/4192).

## 1.1.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3578](https://github.com/DataDog/integrations-core/pull/3578).

## 1.0.0 / 2019-03-29 / Agent 6.11.0

* [Added] Adds Twistlock Integration. See [#3074](https://github.com/DataDog/integrations-core/pull/3074).


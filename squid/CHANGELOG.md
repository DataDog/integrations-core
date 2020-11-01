# CHANGELOG - Squid

## 1.9.0 / 2020-10-31

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).
* [Fixed] Fix version collection. See [#7898](https://github.com/DataDog/integrations-core/pull/7898).

## 1.8.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add config specs. See [#7482](https://github.com/DataDog/integrations-core/pull/7482).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 1.7.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.7.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Fixed] Fix formatting of a log line. See [#6990](https://github.com/DataDog/integrations-core/pull/6990).

## 1.6.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.5.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.5.0 / 2020-02-22 / Agent 7.18.0

* [Added] Add version metadata. See [#5603](https://github.com/DataDog/integrations-core/pull/5603).

## 1.4.1 / 2019-11-07 / Agent 7.16.0

* [Fixed] Adding log section. See [#4824](https://github.com/DataDog/integrations-core/pull/4824).

## 1.4.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.3.0 / 2019-08-24 / Agent 6.14.0

* [Added] Add requests wrapper to squid. See [#4200](https://github.com/DataDog/integrations-core/pull/4200).

## 1.2.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3568](https://github.com/DataDog/integrations-core/pull/3568).

## 1.1.0 / 2019-01-04 / Agent 6.9.0

* [Added] Support Python 3. See [#2788][1].

## 1.0.2 / 2018-09-04 / Agent 6.5.0

* [Fixed] Add data files to the wheel package. See [#1727][2].

## 1.0.1 / 2018-06-07

* [Fixed] Fix bug parsing squid metrics. See [#1643][3]. Thanks [mnussbaum][4].

## 1.0.0 / 2018-02-13

* [FEATURE] adds squid integration.
[1]: https://github.com/DataDog/integrations-core/pull/2788
[2]: https://github.com/DataDog/integrations-core/pull/1727
[3]: https://github.com/DataDog/integrations-core/pull/1643
[4]: https://github.com/mnussbaum

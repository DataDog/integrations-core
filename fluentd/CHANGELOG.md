# CHANGELOG - fluentd

## 1.7.0 / 2020-04-04

* [Added] Add option to set SNI hostname via the `Host` header for RequestsWrapper. See [#5833](https://github.com/DataDog/integrations-core/pull/5833).
* [Added] Add config specs. See [#6147](https://github.com/DataDog/integrations-core/pull/6147).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.6.0 / 2020-03-18

* [Added] Support Fluentd config API endpoint for metadata collection. See [#6062](https://github.com/DataDog/integrations-core/pull/6062).
* [Added] Allow disabling metadata collection in fluentd. See [#6061](https://github.com/DataDog/integrations-core/pull/6061).

## 1.5.0 / 2019-11-26

* [Added] Collect version metadata for Fluentd. See [#5057](https://github.com/DataDog/integrations-core/pull/5057).
* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).

## 1.4.0 / 2019-10-11

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.3.0 / 2019-08-24

* [Added] Fix request wrapper timeout and add test. See [#4375](https://github.com/DataDog/integrations-core/pull/4375).
* [Fixed] Update __init__ method params. See [#4243](https://github.com/DataDog/integrations-core/pull/4243).
* [Added] Add support for proxy settings. See [#3479](https://github.com/DataDog/integrations-core/pull/3479).

## 1.2.0 / 2019-05-14

* [Added] Adhere to code style. See [#3507](https://github.com/DataDog/integrations-core/pull/3507).

## 1.1.1 / 2019-03-29

* [Fixed] Support fluentd v1's monitor_agent metrics. See [#2965](https://github.com/DataDog/integrations-core/pull/2965). Thanks [repeatedly](https://github.com/repeatedly).

## 1.1.0 / 2019-01-04

* [Added] Support Python 3. See [#2735][1].

## 1.0.1 / 2018-09-04

* [Fixed] Add data files to the wheel package. See [#1727][2].

## 1.0.0 / 2017-03-22

* [FEATURE] adds fluentd integration.
[1]: https://github.com/DataDog/integrations-core/pull/2735
[2]: https://github.com/DataDog/integrations-core/pull/1727

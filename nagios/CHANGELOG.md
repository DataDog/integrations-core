# CHANGELOG - nagios

## 1.6.0 / 2020-05-17

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.5.1 / 2019-11-07

* [Fixed] Fix use of format in logging. See [#4973](https://github.com/DataDog/integrations-core/pull/4973).

## 1.5.0 / 2019-11-06

* [Fixed] Refactor tailers logic. See [#4942](https://github.com/DataDog/integrations-core/pull/4942).
* [Added] Support centreon additional field in event logs. See [#4941](https://github.com/DataDog/integrations-core/pull/4941).

## 1.4.1 / 2019-07-04

* [Fixed] Fix event payload so the check name is parsed correctly. See [#3979](https://github.com/DataDog/integrations-core/pull/3979).

## 1.4.0 / 2019-05-14

* [Added] Adhere to code style. See [#3542](https://github.com/DataDog/integrations-core/pull/3542).

## 1.3.0 / 2019-02-18

* [Added] Support Python 3. See [#2835](https://github.com/DataDog/integrations-core/pull/2835).

## 1.2.0 / 2018-12-19

* [Added] Add instance level tags to Nagios Events. See [#2778][1].

## 1.1.3 / 2018-11-30

* [Fixed] Use raw string literals when \ is present. See [#2465][2].

## 1.1.2 / 2018-10-12

* [Fixed] Fix empty event issue with Agent 6. See [#2348][3].

## 1.1.1 / 2018-09-04

* [Fixed] Add Agent 6 compatibility by not sending timestamps for gauge metrics (Agent 6 only). See [#1822][4].
* [Fixed] Add data files to the wheel package. See [#1727][5].

## 1.1.0 / 2018-03-23

* [FEATURE] add custom tag support.

## 1.0.0 / 2017-03-22

* [FEATURE] adds nagios integration.
[1]: https://github.com/DataDog/integrations-core/pull/2778
[2]: https://github.com/DataDog/integrations-core/pull/2465
[3]: https://github.com/DataDog/integrations-core/pull/2348
[4]: https://github.com/DataDog/integrations-core/pull/1822
[5]: https://github.com/DataDog/integrations-core/pull/1727

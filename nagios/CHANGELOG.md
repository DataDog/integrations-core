# CHANGELOG - nagios

## 1.10.0-rc.1 / 2021-09-23


## 1.9.0-rc.1 / 2021-09-23

* [Added] Disable generic tags. See [#10027](https://github.com/DataDog/integrations-core/pull/10027).

## 1.8.0 / 2021-05-28 / Agent 7.29.0

* [Added] Add runtime configuration validation. See [#8959](https://github.com/DataDog/integrations-core/pull/8959).

## 1.7.1 / 2021-03-07 / Agent 7.27.0

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.7.0 / 2020-12-11 / Agent 7.25.0

* [Added] Add log support. See [#8100](https://github.com/DataDog/integrations-core/pull/8100).
* [Added] Add config specs. See [#7978](https://github.com/DataDog/integrations-core/pull/7978).

## 1.6.2 / 2020-09-04 / Agent 7.23.0

* [Fixed] Fix tailer on missing file. See [#7447](https://github.com/DataDog/integrations-core/pull/7447).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 1.6.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Fix logging. See [#7239](https://github.com/DataDog/integrations-core/pull/7239).

## 1.6.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.5.1 / 2019-11-07 / Agent 7.16.0

* [Fixed] Fix use of format in logging. See [#4973](https://github.com/DataDog/integrations-core/pull/4973).

## 1.5.0 / 2019-11-06

* [Fixed] Refactor tailers logic. See [#4942](https://github.com/DataDog/integrations-core/pull/4942).
* [Added] Support centreon additional field in event logs. See [#4941](https://github.com/DataDog/integrations-core/pull/4941).

## 1.4.1 / 2019-07-04 / Agent 6.13.0

* [Fixed] Fix event payload so the check name is parsed correctly. See [#3979](https://github.com/DataDog/integrations-core/pull/3979).

## 1.4.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3542](https://github.com/DataDog/integrations-core/pull/3542).

## 1.3.0 / 2019-02-18 / Agent 6.10.0

* [Added] Support Python 3. See [#2835](https://github.com/DataDog/integrations-core/pull/2835).

## 1.2.0 / 2018-12-19 / Agent 6.9.0

* [Added] Add instance level tags to Nagios Events. See [#2778][1].

## 1.1.3 / 2018-11-30 / Agent 6.8.0

* [Fixed] Use raw string literals when \ is present. See [#2465][2].

## 1.1.2 / 2018-10-12 / Agent 6.6.0

* [Fixed] Fix empty event issue with Agent 6. See [#2348][3].

## 1.1.1 / 2018-09-04 / Agent 6.5.0

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

# CHANGELOG - windows_service

## 2.6.0 / 2020-05-17

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.5.2 / 2020-04-04

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 2.5.1 / 2020-02-25

* [Fixed] Bump minimun agent version. See [#5834](https://github.com/DataDog/integrations-core/pull/5834).

## 2.5.0 / 2020-02-22

* [Deprecated] Deprecate `service` tag. See [#5545](https://github.com/DataDog/integrations-core/pull/5545).

## 2.4.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 2.3.0 / 2019-12-02

* [Added] Upgrade pywin32 to 227. See [#5036](https://github.com/DataDog/integrations-core/pull/5036).

## 2.2.0 / 2019-10-11

* [Added] Upgrade pywin32 to 225. See [#4563](https://github.com/DataDog/integrations-core/pull/4563).
* [Fixed] Search patterns in reverse sort order. See [#4503](https://github.com/DataDog/integrations-core/pull/4503).

## 2.1.0 / 2019-05-14

* [Fixed] Add debug to compare short names, service names and patterns. See [#3427](https://github.com/DataDog/integrations-core/pull/3427).
* [Added] Adhere to code style. See [#3583](https://github.com/DataDog/integrations-core/pull/3583).

## 2.0.0 / 2018-10-12

* [Added] Pin pywin32 dependency. See [#2322][1].
* [Removed] Make windows_service use scm api instead of wmi. See [#2305][2].

## 1.2.1 / 2018-09-04

* [Fixed] Add data files to the wheel package. See [#1727][3].

## 1.2.0 / 2018-03-23

* [FEATURE] adds custom tag support

## 1.1.1 / 2018-02-13

* [FEATURE] Allow wildcards for service names
* [FEATURE] Allow ALL for service names to report all registered services.

## 1.0.0 / 2017-03-22

* [FEATURE] adds windows_service integration.
[1]: https://github.com/DataDog/integrations-core/pull/2322
[2]: https://github.com/DataDog/integrations-core/pull/2305
[3]: https://github.com/DataDog/integrations-core/pull/1727

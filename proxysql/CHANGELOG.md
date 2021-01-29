# CHANGELOG - ProxySQL

## 3.0.0 / 2021-01-25

* [Added] Add version verification for datadog-checks-base. See [#8255](https://github.com/DataDog/integrations-core/pull/8255).
* [Changed] Update ProxySQL check to use TLS context wrapper. See [#8243](https://github.com/DataDog/integrations-core/pull/8243).

## 2.0.0 / 2020-10-31 / Agent 7.24.0

* [Fixed] Fix config typo. See [#7843](https://github.com/DataDog/integrations-core/pull/7843).
* [Changed] QueryManager - Prevent queries leaking between check instances. See [#7750](https://github.com/DataDog/integrations-core/pull/7750).

## 1.2.2 / 2020-09-21 / Agent 7.23.0

* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 1.2.1 / 2020-07-03 / Agent 7.21.0

* [Fixed] Revert/Remove unnecessary `database_name` config. See [#7049](https://github.com/DataDog/integrations-core/pull/7049).

## 1.2.0 / 2020-06-29

* [Added] Allow proxysql checks to specify stats database name. See [#6835](https://github.com/DataDog/integrations-core/pull/6835). Thanks [tabacco](https://github.com/tabacco).

## 1.1.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.0.0 / 2020-04-03 / Agent 7.19.0

* [Added] New Integration ProxySQL. See [#6144](https://github.com/DataDog/integrations-core/pull/6144).

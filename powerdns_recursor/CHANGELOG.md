# CHANGELOG - powerdns_recursor

## 1.10.0 / 2021-10-04

* [Added] Add HTTP option to control the size of streaming responses. See [#10183](https://github.com/DataDog/integrations-core/pull/10183).
* [Added] Add allow_redirect option. See [#10160](https://github.com/DataDog/integrations-core/pull/10160).
* [Added] Disable generic tags. See [#10027](https://github.com/DataDog/integrations-core/pull/10027).
* [Fixed] Fix the description of the `allow_redirects` HTTP option. See [#10195](https://github.com/DataDog/integrations-core/pull/10195).

## 1.9.0 / 2021-04-19 / Agent 7.28.0

* [Added] Add runtime configuration validation. See [#8972](https://github.com/DataDog/integrations-core/pull/8972).

## 1.8.1 / 2021-03-07 / Agent 7.27.0

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 1.8.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Added] Add config spec. See [#7742](https://github.com/DataDog/integrations-core/pull/7742).

## 1.7.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.7.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).
* [Added] Add version metadata. See [#6916](https://github.com/DataDog/integrations-core/pull/6916).

## 1.6.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.5.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.5.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.4.0 / 2019-08-24 / Agent 6.14.0

* [Added] Add requests wrapper to powerdns_recursor. See [#4261](https://github.com/DataDog/integrations-core/pull/4261).

## 1.3.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3558](https://github.com/DataDog/integrations-core/pull/3558).

## 1.2.0 / 2019-01-04 / Agent 6.9.0

* [Added] Support Python 3. See [#2789][1].

## 1.1.1 / 2018-09-04 / Agent 6.5.0

* [Fixed] Make sure all checks' versions are exposed. See [#1945][2].
* [Fixed] Add data files to the wheel package. See [#1727][3].

## 1.1.0 / 2018-05-11

* [FEATURE] adds custom tag support for service checks.

## 1.0.0 / 2017-03-22

* [FEATURE] adds powerdns_recursor integration.
[1]: https://github.com/DataDog/integrations-core/pull/2789
[2]: https://github.com/DataDog/integrations-core/pull/1945
[3]: https://github.com/DataDog/integrations-core/pull/1727

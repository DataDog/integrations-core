# CHANGELOG - tcp_check

## 2.6.0 / 2020-09-21

* [Added] Add config spec. See [#7531](https://github.com/DataDog/integrations-core/pull/7531).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 2.5.0 / 2020-06-16 / Agent 7.21.0

* [Added] Use higher precision clock measurements for Python 3. See [#6849](https://github.com/DataDog/integrations-core/pull/6849).

## 2.4.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 2.3.4 / 2020-03-11 / Agent 7.19.0

* [Fixed] Reattempt to resolve IP on failure. See [#6012](https://github.com/DataDog/integrations-core/pull/6012).

## 2.3.3 / 2019-12-24 / Agent 7.17.0

* [Fixed] Don't report response time when connection fails. See [#5271](https://github.com/DataDog/integrations-core/pull/5271).

## 2.3.2 / 2019-12-17

* [Fixed] Fix service_checks submission. See [#5229](https://github.com/DataDog/integrations-core/pull/5229).

## 2.3.1 / 2019-10-11 / Agent 6.15.0

* [Fixed] Remove legacy network check tcp. See [#4580](https://github.com/DataDog/integrations-core/pull/4580).

## 2.3.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3574](https://github.com/DataDog/integrations-core/pull/3574).

## 2.2.1 / 2019-03-29 / Agent 6.11.0

* [Fixed] ensure_unicode with normalize for py3 compatibility. See [#3218](https://github.com/DataDog/integrations-core/pull/3218).

## 2.2.0 / 2019-02-18 / Agent 6.10.0

* [Added] Support Python 3. See [#2964](https://github.com/DataDog/integrations-core/pull/2964).

## 2.1.0 / 2018-11-30 / Agent 6.8.0

* [Added] Send service check as metric. See [#2509][1].

## 2.0.2 / 2018-09-04 / Agent 6.5.0

* [Fixed] Add data files to the wheel package. See [#1727][2].

## 2.0.1 / 2018-06-20 / Agent 6.4.0

* [Fixed] Fix error message when TCP check fails. See [#1745][3]. Thanks [Siecje][4].

## 2.0.0 / 2018-03-23

* [DEPRECATION] Remove the `skip_event` option from the check. See [#1054][5]

## 1.0.0 / 2017-03-22

* [FEATURE] adds tcp_check integration.
[1]: https://github.com/DataDog/integrations-core/pull/2509
[2]: https://github.com/DataDog/integrations-core/pull/1727
[3]: https://github.com/DataDog/integrations-core/pull/1745
[4]: https://github.com/Siecje
[5]: https://github.com/DataDog/integrations-core/pull/1054

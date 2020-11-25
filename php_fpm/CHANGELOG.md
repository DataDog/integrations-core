# CHANGELOG - php_fpm

## 1.11.0 / 2020-10-31

* [Added] Add config spec. See [#7879](https://github.com/DataDog/integrations-core/pull/7879).
* [Fixed] Add missing default HTTP headers: Accept, Accept-Encoding. See [#7725](https://github.com/DataDog/integrations-core/pull/7725).

## 1.10.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 1.10.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).

## 1.9.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.8.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.8.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 1.7.0 / 2019-10-11 / Agent 6.15.0

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.6.0 / 2019-08-24 / Agent 6.14.0

* [Added] Add request wrappers to php_fpm. See [#4264](https://github.com/DataDog/integrations-core/pull/4264).

## 1.5.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3555](https://github.com/DataDog/integrations-core/pull/3555).

## 1.4.1 / 2019-03-29 / Agent 6.11.0

* [Fixed] Properly ship flup on Python 3. See [#3304](https://github.com/DataDog/integrations-core/pull/3304).

## 1.4.0 / 2018-11-27 / Agent 6.8.0

* [Added] Added unix socket support. See [#2636][1]. Thanks [pperegrina][2].

## 1.3.1 / 2018-10-12 / Agent 6.6.0

* [Fixed] Make the status route-agnostic when using fastcgi. See [#2282][3].

## 1.3.0 / 2018-09-04 / Agent 6.5.0

* [Added] Support fastcgi requests. See [#1997][4].

## 1.2.0 / 2018-07-06 / Agent 6.4.0

* [Added] Add exponential backoff when status returns 503. See [#1851][5].
* [Changed] Add data files to the wheel package. See [#1727][6].

## 1.1.0 / 2018-01-10

* [IMPROVEMENT] Adds a timeout parameter. See #206, thanks @toksvaeth.
* [IMPROVEMENT] Adds the ability to skip SSL validation. See #941, thanks @dntbrme.

## 1.0.0 / 2017-03-22

* [FEATURE] adds php_fpm integration.
[1]: https://github.com/DataDog/integrations-core/pull/2636
[2]: https://github.com/pperegrina
[3]: https://github.com/DataDog/integrations-core/pull/2282
[4]: https://github.com/DataDog/integrations-core/pull/1997
[5]: https://github.com/DataDog/integrations-core/pull/1851
[6]: https://github.com/DataDog/integrations-core/pull/1727

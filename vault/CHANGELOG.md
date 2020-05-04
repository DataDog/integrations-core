# CHANGELOG - Vault

## 2.3.2 / 2020-05-04

* [Fixed] Fixed infinite stream of Vault leader detection events. See [#6552](https://github.com/DataDog/integrations-core/pull/6552). Thanks [fabienrenaud](https://github.com/fabienrenaud).

## 2.3.1 / 2020-04-07

* [Fixed] Add `kerberos_cache` to HTTP config options. See [#6279](https://github.com/DataDog/integrations-core/pull/6279).

## 2.3.0 / 2020-04-04

* [Added] Add option to set SNI hostname via the `Host` header for RequestsWrapper. See [#5833](https://github.com/DataDog/integrations-core/pull/5833).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).
* [Fixed] Fix event submission on leader change. See [#6039](https://github.com/DataDog/integrations-core/pull/6039).

## 2.2.1 / 2020-02-25

* [Fixed] Update datadog_checks_base dependencies. See [#5846](https://github.com/DataDog/integrations-core/pull/5846).

## 2.2.0 / 2020-02-22

* [Added] Add `service` option to default configuration. See [#5805](https://github.com/DataDog/integrations-core/pull/5805).
* [Added] Add missing vault summary metric. See [#5670](https://github.com/DataDog/integrations-core/pull/5670).

## 2.1.2 / 2020-01-24

* [Fixed] Send summary count metrics as a count. See [#5538](https://github.com/DataDog/integrations-core/pull/5538).

## 2.1.1 / 2020-01-13

* [Fixed] Fix http handler. See [#5434](https://github.com/DataDog/integrations-core/pull/5434).

## 2.1.0 / 2020-01-09

* [Added] Add support for metric collection without a token. See [#5424](https://github.com/DataDog/integrations-core/pull/5424).
* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).

## 2.0.0 / 2019-12-21

* [Changed] Collect prometheus metrics if a client token is available. See [#5177](https://github.com/DataDog/integrations-core/pull/5177).

## 1.7.1 / 2019-10-21

* [Fixed] Fix is_leader when vault sealed. See [#4838](https://github.com/DataDog/integrations-core/pull/4838).

## 1.7.0 / 2019-10-18

* [Added] Allows certain expected HTTP error status_codes for the `/sys/health` endpoint. See [#4745](https://github.com/DataDog/integrations-core/pull/4745).

## 1.6.0 / 2019-10-07

* [Fixed] Fix crash in HA mode. See [#4698](https://github.com/DataDog/integrations-core/pull/4698).
* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 1.5.0 / 2019-08-24

* [Added] Add requests wrapper to vault. See [#4259](https://github.com/DataDog/integrations-core/pull/4259).

## 1.4.1 / 2019-07-31

* [Fixed] Submit critical service check with 500 server errors. See [#4242](https://github.com/DataDog/integrations-core/pull/4242).

## 1.4.0 / 2019-05-14

* [Added] Adhere to code style. See [#3580](https://github.com/DataDog/integrations-core/pull/3580).

## 1.3.1 / 2019-01-04

* [Fixed] Fix unsupported API version fallback. See [#2793][1].

## 1.3.0 / 2018-11-30

* [Added] Support custom certificates. See [#2657][2]. Thanks [eedwards-sk][3].

## 1.2.0 / 2018-08-15

* [Added] Add is_leader metric. See [#2057][4].

## 1.1.0 / 2018-08-08

* [Added] Add option to disable urllib3 warnings. See [#2009][5].
* [Changed] Add data files to the wheel package. See [#1727][6].

## 1.0.0 / 2018-06-19

* [Added] Add Vault integration. See [#1759][7].
[1]: https://github.com/DataDog/integrations-core/pull/2793
[2]: https://github.com/DataDog/integrations-core/pull/2657
[3]: https://github.com/eedwards-sk
[4]: https://github.com/DataDog/integrations-core/pull/2057
[5]: https://github.com/DataDog/integrations-core/pull/2009
[6]: https://github.com/DataDog/integrations-core/pull/1727
[7]: https://github.com/DataDog/integrations-core/pull/1759

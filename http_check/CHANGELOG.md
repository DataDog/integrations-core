# CHANGELOG - http_check

## 5.1.0 / 2021-01-28

* [Security] Upgrade cryptography python package. See [#8476](https://github.com/DataDog/integrations-core/pull/8476).

## 5.0.0 / 2021-01-21

* [Added] Support combined client cert files. See [#8298](https://github.com/DataDog/integrations-core/pull/8298).
* [Fixed] Fix misleading debug message. See [#8379](https://github.com/DataDog/integrations-core/pull/8379).
* [Changed] Update http_check to use TLS context wrapper. See [#8268](https://github.com/DataDog/integrations-core/pull/8268).
* [Changed] Only send ssl metrics if a connection succeeded. See [#8102](https://github.com/DataDog/integrations-core/pull/8102).

## 4.12.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add support for OPTIONS method. See [#7894](https://github.com/DataDog/integrations-core/pull/7894).
* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Security] Upgrade `cryptography` dependency. See [#7869](https://github.com/DataDog/integrations-core/pull/7869).

## 4.11.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Do not render null defaults for config spec example consumer. See [#7503](https://github.com/DataDog/integrations-core/pull/7503).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 4.10.0 / 2020-08-10 / Agent 7.22.0

* [Added] Add config specs to http check. See [#7245](https://github.com/DataDog/integrations-core/pull/7245).
* [Fixed] Update ntlm_domain example. See [#7118](https://github.com/DataDog/integrations-core/pull/7118).

## 4.9.1 / 2020-07-09

* [Fixed] Raise http service check message limit. See [#7008](https://github.com/DataDog/integrations-core/pull/7008).

## 4.9.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).

## 4.8.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 4.7.1 / 2020-04-09 / Agent 7.19.0

* [Fixed] Fix new option name in config sample. See [#6296](https://github.com/DataDog/integrations-core/pull/6296).

## 4.7.0 / 2020-04-04

* [Added] Add option to set SNI hostname via the `Host` header for RequestsWrapper. See [#5833](https://github.com/DataDog/integrations-core/pull/5833).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Update reference to `disable_ssl_validation`. See [#5945](https://github.com/DataDog/integrations-core/pull/5945).

## 4.6.4 / 2020-02-22 / Agent 7.18.0

* [Fixed] Apply strptime thread-safety fix only on Python 2. See [#5618](https://github.com/DataDog/integrations-core/pull/5618).

## 4.6.3 / 2020-01-24 / Agent 7.17.0

* [Fixed] Document that tls_verify is False by default. See [#5547](https://github.com/DataDog/integrations-core/pull/5547).

## 4.6.2 / 2020-01-21

* [Fixed] Properly enable TLS/SSL verification when `tls_verify` is true. See [#5507](https://github.com/DataDog/integrations-core/pull/5507).

## 4.6.1 / 2020-01-17

* [Fixed] Avoid cross instance data sharing. See [#5499](https://github.com/DataDog/integrations-core/pull/5499).

## 4.6.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 4.5.0 / 2019-12-02 / Agent 7.16.0

* [Added] Upgrade cryptography to 2.8. See [#5047](https://github.com/DataDog/integrations-core/pull/5047).

## 4.4.0 / 2019-11-15

* [Fixed] Update response_time metric source. See [#5025](https://github.com/DataDog/integrations-core/pull/5025).
* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).
* [Fixed] Improve config constructor syntax. See [#4841](https://github.com/DataDog/integrations-core/pull/4841).

## 4.3.1 / 2019-10-18 / Agent 6.15.0

* [Fixed] Ensure the correct tls_ca_cert value is used. See [#4819](https://github.com/DataDog/integrations-core/pull/4819).

## 4.3.0 / 2019-10-11

* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).

## 4.2.0 / 2019-08-24 / Agent 6.14.0

* [Added] Add request wrapper to http_check. See [#4363](https://github.com/DataDog/integrations-core/pull/4363).

## 4.1.1 / 2019-07-22 / Agent 6.13.0

* [Fixed] Fix detection of the embedded Agent directory. See [#4158](https://github.com/DataDog/integrations-core/pull/4158).

## 4.1.0 / 2019-07-04

* [Added] Update cryptography version. See [#4000](https://github.com/DataDog/integrations-core/pull/4000).

## 4.0.0 / 2019-05-14 / Agent 6.12.0

* [Changed] Remove every default header except `User-Agent`. See [#3644](https://github.com/DataDog/integrations-core/pull/3644).
* [Added] Adhere to code style. See [#3516](https://github.com/DataDog/integrations-core/pull/3516).

## 3.2.1 / 2019-03-29 / Agent 6.11.0

* [Fixed] Fix Python 3.7 support. See [#3293](https://github.com/DataDog/integrations-core/pull/3293).
* [Fixed] ensure_unicode with normalize for py3 compatibility. See [#3218](https://github.com/DataDog/integrations-core/pull/3218).

## 3.2.0 / 2019-02-18 / Agent 6.10.0

* [Added] Add url as tag. See [#3080](https://github.com/DataDog/integrations-core/pull/3080).
* [Added] [http_check] adds instance tag to metrics. See [#3065](https://github.com/DataDog/integrations-core/pull/3065).

## 3.1.1 / 2018-12-07 / Agent 6.8.0

* [Fixed] Fix unicode handling of log messages. See [#2700][1].

## 3.1.0 / 2018-11-30

* [Added] Add option to set `stream` parameter on requests. See [#2658][2]. Thanks [syskill][3].
* [Added] Upgrade cryptography. See [#2659][4].
* [Added] Upgrade requests. See [#2481][5].
* [Fixed] Use raw string literals when \ is present. See [#2465][6].
* [Added] Fix unicode handling on A6. See [#2435][7].
* [Added] Validate that the url starts with the scheme. See [#2393][8].

## 3.0.0 / 2018-10-12 / Agent 6.6.0

* [Added] Handle SSL exception and send a DOWN service check status. See [#2332][9].
* [Changed] Refactoring: isolate config parsing. See [#2321][10].

## 2.4.0 / 2018-10-01

* [Fixed] Fix fetching ca_certs from init_config. See [#2318][11].
* [Added] Allow configuring cert expiration time in seconds. See [#2290][12].

## 2.3.0 / 2018-09-04 / Agent 6.5.0

* [Fixed] Update cryptography to 2.3. See [#1927][13].
* [Fixed] fix link in config option description. See [#1865][14].
* [Added] support NTLM auth. See [#1812][15].
* [Fixed] Add data files to the wheel package. See [#1727][16].

## 2.2.0 / 2018-06-20 / Agent 6.3.1

* [Fixed] Add support client auth for http check cert expiration.. See [#1754][17].
* [Fixed] Check will now send data with PUT, DELETE, and PATCH methods--not just POST. See [#1718][18].

## 2.1.0 / 2018-06-06

* [Fixed] fixes AttributeError when running on 6.2.1. See [#1617][19].
* [Fixed] Suppress InsecureRequestWarning for urllib3 for http_check. See [#1574][20].
* [Added] Allow users to disable matching hostnames verification in ssl cert verification. See [#1519][21].
* [Changed] Emit a warning if disable_ssl_validation is unset. See [#1517][22].

## 2.0.1 / 2018-05-11

* [BUGFIX] Properly detect default certificate file for all supported Platforms. See [#1340][23]

## 2.0.0 / 2018-03-23

* [BUGFIX] Make import of default certificate file relative rather than absolute
  Fixes loading problem on Windows, and/or allows check to be installed in other
  location
* [DEPRECATION] Remove the `skip_event` option from the check. See [#1054][24]

## 1.4.0 / 2018-02-13

* [IMPROVEMENT] begin deprecation of `no_proxy` config flag in favor of `skip_proxy`. See [#1057][25].

## 1.3.1 / 2018-01-17

* [BUGFIX] Use lowercase in an `if statement` for a user defined HTTP method.

## 1.3.0 / 2018-01-10

* [FEATURE] Report http connect status as metrics. See #659.
* [BUGFIX] User-defined "url" tag replaces default "url" tag. See[#301][26]. (Thanks [@colinmollenhour][27])
* [FEATURE] Add configurable ssl server name for cert expiration check. See[#905][28].

## 1.2.0 / 2017-10-10

* [FEATURE] Add support for client side certificate. See[#688][29]. (Thanks [@xkrt][30])
* [IMPROVEMENT] Make tornado optional. See [#758][31].

## 1.1.2 / 2017-08-28

* [IMPROVEMENT] Improved logging. See [#652][32].

## 1.1.1 / 2017-07-18

* [BUGFIX] Fix response tuple arity in SSL certificate check. See[#461][33].

## 1.1.0 / 2017-06-05

* [FEATURE] Add support for SOAP requests. See [#328][34].
* [FEATURE] Add gauge metric for ssl days left. See [#249][35].

## 1.0.0 / 2017-03-22

* [FEATURE] adds http_check integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2700
[2]: https://github.com/DataDog/integrations-core/pull/2658
[3]: https://github.com/syskill
[4]: https://github.com/DataDog/integrations-core/pull/2659
[5]: https://github.com/DataDog/integrations-core/pull/2481
[6]: https://github.com/DataDog/integrations-core/pull/2465
[7]: https://github.com/DataDog/integrations-core/pull/2435
[8]: https://github.com/DataDog/integrations-core/pull/2393
[9]: https://github.com/DataDog/integrations-core/pull/2332
[10]: https://github.com/DataDog/integrations-core/pull/2321
[11]: https://github.com/DataDog/integrations-core/pull/2318
[12]: https://github.com/DataDog/integrations-core/pull/2290
[13]: https://github.com/DataDog/integrations-core/pull/1927
[14]: https://github.com/DataDog/integrations-core/pull/1865
[15]: https://github.com/DataDog/integrations-core/pull/1812
[16]: https://github.com/DataDog/integrations-core/pull/1727
[17]: https://github.com/DataDog/integrations-core/pull/1754
[18]: https://github.com/DataDog/integrations-core/pull/1718
[19]: https://github.com/DataDog/integrations-core/pull/1617
[20]: https://github.com/DataDog/integrations-core/pull/1574
[21]: https://github.com/DataDog/integrations-core/pull/1519
[22]: https://github.com/DataDog/integrations-core/pull/1517
[23]: https://github.com/DataDog/integrations-core/pull/1340
[24]: https://github.com/DataDog/integrations-core/pull/1054
[25]: https://github.com/DataDog/integrations-core/pull/1057
[26]: https://github.com/DataDog/integrations-core/pull/301
[27]: https://github.com/colinmollenhour
[28]: https://github.com/DataDog/integrations-core/pull/905
[29]: https://github.com/DataDog/integrations-core/issues/688
[30]: https://github.com/xkrt
[31]: https://github.com/DataDog/integrations-core/issues/758
[32]: https://github.com/DataDog/integrations-core/issues/652
[33]: https://github.com/DataDog/integrations-core/issues/461
[34]: https://github.com/DataDog/integrations-core/issues/328
[35]: https://github.com/DataDog/integrations-core/issues/249

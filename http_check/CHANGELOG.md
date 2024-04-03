# CHANGELOG - http_check

<!-- towncrier release notes start -->

## 9.5.0 / 2024-03-07 / Agent 7.52.0

***Security***:

* Bump cryptography to 42.0.5 ([#17054](https://github.com/DataDog/integrations-core/pull/17054))

## 9.4.0 / 2024-02-16

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 9.3.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Update dependencies ([#16448](https://github.com/DataDog/integrations-core/pull/16448))

## 9.2.3 / 2023-12-04 / Agent 7.50.0

***Fixed***:

* Bump the cryptography version to 41.0.6 ([#16322](https://github.com/DataDog/integrations-core/pull/16322))

## 9.2.2 / 2023-11-10

***Fixed***:

* Allow using an integer for the expected status code in the config ([#16163](https://github.com/DataDog/integrations-core/pull/16163))

## 9.2.1 / 2023-10-26 / Agent 7.49.0

***Fixed***:

* Bump the `cryptography` version to 41.0.5 ([#16083](https://github.com/DataDog/integrations-core/pull/16083))

## 9.2.0 / 2023-09-29

***Added***:

* Update Cryptography to 41.0.4 ([#15922](https://github.com/DataDog/integrations-core/pull/15922))

## 9.1.0 / 2023-09-08

***Added***:

* Add `use_cert_from_response` option ([#15785](https://github.com/DataDog/integrations-core/pull/15785))

## 9.0.1 / 2023-08-18 / Agent 7.48.0

***Fixed***:

* Bump cryptography to 41.0.3 ([#15517](https://github.com/DataDog/integrations-core/pull/15517))

## 9.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 8.3.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 8.2.1 / 2023-03-03 / Agent 7.44.0

***Fixed***:

* Support case-insensitive header fields ([#13876](https://github.com/DataDog/integrations-core/pull/13876))

## 8.2.0 / 2023-01-20 / Agent 7.43.0

***Added***:

* Allow certificate expiration checks no matter what ssl/tls verification settings are ([#13527](https://github.com/DataDog/integrations-core/pull/13527)) Thanks [scott-shields-github](https://github.com/scott-shields-github).

## 8.1.1 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Update cryptography dependency ([#13367](https://github.com/DataDog/integrations-core/pull/13367))

## 8.1.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

## 8.0.1 / 2022-05-23 / Agent 7.37.0

***Fixed***:

* Clarify no cert service check message ([#12064](https://github.com/DataDog/integrations-core/pull/12064))

## 8.0.0 / 2022-05-15

***Removed***:

* Delete unused `weakciphers` option path ([#11926](https://github.com/DataDog/integrations-core/pull/11926))

***Fixed***:

* Don't pin urllib3 ([#11944](https://github.com/DataDog/integrations-core/pull/11944))

## 7.1.1 / 2022-04-11 / Agent 7.36.0

***Fixed***:

* Improve service check message when cert is not found ([#11793](https://github.com/DataDog/integrations-core/pull/11793))

## 7.1.0 / 2022-04-05

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Document TLS options ([#11714](https://github.com/DataDog/integrations-core/pull/11714))
* Remap `check_hostname` to `tls_validate_hostname`  ([#11706](https://github.com/DataDog/integrations-core/pull/11706))
* Fail more gracefully ([#11615](https://github.com/DataDog/integrations-core/pull/11615))

## 7.0.1 / 2022-03-02

***Fixed***:

* Avoid reading response content unless necessary ([#11590](https://github.com/DataDog/integrations-core/pull/11590))
* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 7.0.0 / 2022-03-02 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11365](https://github.com/DataDog/integrations-core/pull/11365))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 6.1.2 / 2022-01-08 / Agent 7.33.0

***Fixed***:

* Add urllib3 as dependency ([#11069](https://github.com/DataDog/integrations-core/pull/11069))
* Fix urllib3 import statement ([#11065](https://github.com/DataDog/integrations-core/pull/11065))
* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 6.1.1 / 2021-10-18

***Fixed***:

* Avoid resetting auth token on headers ([#10388](https://github.com/DataDog/integrations-core/pull/10388))

## 6.1.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Update dependencies ([#10228](https://github.com/DataDog/integrations-core/pull/10228))
* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Bump base package dependency ([#10218](https://github.com/DataDog/integrations-core/pull/10218))
* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 6.0.0 / 2021-08-22 / Agent 7.31.0

***Changed***:

* Remove messages for integrations for OK service checks ([#9888](https://github.com/DataDog/integrations-core/pull/9888))

## 5.3.2 / 2021-06-07 / Agent 7.29.0

***Fixed***:

* Fix data configuration type ([#9482](https://github.com/DataDog/integrations-core/pull/9482))

## 5.3.1 / 2021-04-20 / Agent 7.28.0

***Fixed***:

* Restore correct default value of tls_verify ([#9197](https://github.com/DataDog/integrations-core/pull/9197))

## 5.3.0 / 2021-04-19

***Added***:

* Upgrade cryptography to 3.4.6 on Python 3 ([#8764](https://github.com/DataDog/integrations-core/pull/8764))
* Add runtime configuration validation ([#8932](https://github.com/DataDog/integrations-core/pull/8932))

## 5.2.0 / 2021-03-07 / Agent 7.27.0

***Security***:

* Upgrade cryptography python package ([#8611](https://github.com/DataDog/integrations-core/pull/8611))

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 5.1.0 / 2021-01-28 / Agent 7.26.0

***Security***:

* Upgrade cryptography python package ([#8476](https://github.com/DataDog/integrations-core/pull/8476))

## 5.0.0 / 2021-01-21

***Changed***:

* Update http_check to use TLS context wrapper ([#8268](https://github.com/DataDog/integrations-core/pull/8268))
* Only send ssl metrics if a connection succeeded ([#8102](https://github.com/DataDog/integrations-core/pull/8102))

***Added***:

* Support combined client cert files ([#8298](https://github.com/DataDog/integrations-core/pull/8298))

***Fixed***:

* Fix misleading debug message ([#8379](https://github.com/DataDog/integrations-core/pull/8379))

## 4.12.0 / 2020-10-31 / Agent 7.24.0

***Security***:

* Upgrade `cryptography` dependency ([#7869](https://github.com/DataDog/integrations-core/pull/7869))

***Added***:

* Add support for OPTIONS method ([#7894](https://github.com/DataDog/integrations-core/pull/7894))
* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))

## 4.11.0 / 2020-09-21 / Agent 7.23.0

***Added***:

* Add RequestsWrapper option to support UTF-8 for basic auth ([#7441](https://github.com/DataDog/integrations-core/pull/7441))

***Fixed***:

* Do not render null defaults for config spec example consumer ([#7503](https://github.com/DataDog/integrations-core/pull/7503))
* Update proxy section in conf.yaml ([#7336](https://github.com/DataDog/integrations-core/pull/7336))

## 4.10.0 / 2020-08-10 / Agent 7.22.0

***Added***:

* Add config specs to http check ([#7245](https://github.com/DataDog/integrations-core/pull/7245))

***Fixed***:

* Update ntlm_domain example ([#7118](https://github.com/DataDog/integrations-core/pull/7118))

## 4.9.1 / 2020-07-09

***Fixed***:

* Raise http service check message limit ([#7008](https://github.com/DataDog/integrations-core/pull/7008))

## 4.9.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Add note about warning concurrency ([#6967](https://github.com/DataDog/integrations-core/pull/6967))

## 4.8.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 4.7.1 / 2020-04-09 / Agent 7.19.0

***Fixed***:

* Fix new option name in config sample ([#6296](https://github.com/DataDog/integrations-core/pull/6296))

## 4.7.0 / 2020-04-04

***Added***:

* Add option to set SNI hostname via the `Host` header for RequestsWrapper ([#5833](https://github.com/DataDog/integrations-core/pull/5833))

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))
* Update reference to `disable_ssl_validation` ([#5945](https://github.com/DataDog/integrations-core/pull/5945))

## 4.6.4 / 2020-02-22 / Agent 7.18.0

***Fixed***:

* Apply strptime thread-safety fix only on Python 2 ([#5618](https://github.com/DataDog/integrations-core/pull/5618))

## 4.6.3 / 2020-01-24 / Agent 7.17.0

***Fixed***:

* Document that tls_verify is False by default ([#5547](https://github.com/DataDog/integrations-core/pull/5547))

## 4.6.2 / 2020-01-21

***Fixed***:

* Properly enable TLS/SSL verification when `tls_verify` is true ([#5507](https://github.com/DataDog/integrations-core/pull/5507))

## 4.6.1 / 2020-01-17

***Fixed***:

* Avoid cross instance data sharing ([#5499](https://github.com/DataDog/integrations-core/pull/5499))

## 4.6.0 / 2020-01-13

***Added***:

* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 4.5.0 / 2019-12-02 / Agent 7.16.0

***Added***:

* Upgrade cryptography to 2.8 ([#5047](https://github.com/DataDog/integrations-core/pull/5047))

## 4.4.0 / 2019-11-15

***Added***:

* Add auth type to RequestsWrapper ([#4708](https://github.com/DataDog/integrations-core/pull/4708))

***Fixed***:

* Update response_time metric source ([#5025](https://github.com/DataDog/integrations-core/pull/5025))
* Improve config constructor syntax ([#4841](https://github.com/DataDog/integrations-core/pull/4841))

## 4.3.1 / 2019-10-18 / Agent 6.15.0

***Fixed***:

* Ensure the correct tls_ca_cert value is used ([#4819](https://github.com/DataDog/integrations-core/pull/4819))

## 4.3.0 / 2019-10-11

***Added***:

* Add option to override KRB5CCNAME env var ([#4578](https://github.com/DataDog/integrations-core/pull/4578))

## 4.2.0 / 2019-08-24 / Agent 6.14.0

***Added***:

* Add request wrapper to http_check ([#4363](https://github.com/DataDog/integrations-core/pull/4363))

## 4.1.1 / 2019-07-22 / Agent 6.13.0

***Fixed***:

* Fix detection of the embedded Agent directory ([#4158](https://github.com/DataDog/integrations-core/pull/4158))

## 4.1.0 / 2019-07-04

***Added***:

* Update cryptography version ([#4000](https://github.com/DataDog/integrations-core/pull/4000))

## 4.0.0 / 2019-05-14 / Agent 6.12.0

***Changed***:

* Remove every default header except `User-Agent` ([#3644](https://github.com/DataDog/integrations-core/pull/3644))

***Added***:

* Adhere to code style ([#3516](https://github.com/DataDog/integrations-core/pull/3516))

## 3.2.1 / 2019-03-29 / Agent 6.11.0

***Fixed***:

* Fix Python 3.7 support ([#3293](https://github.com/DataDog/integrations-core/pull/3293))
* ensure_unicode with normalize for py3 compatibility ([#3218](https://github.com/DataDog/integrations-core/pull/3218))

## 3.2.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Add url as tag ([#3080](https://github.com/DataDog/integrations-core/pull/3080))
* [http_check] adds instance tag to metrics ([#3065](https://github.com/DataDog/integrations-core/pull/3065))

## 3.1.1 / 2018-12-07 / Agent 6.8.0

***Fixed***:

* Fix unicode handling of log messages ([#2700](https://github.com/DataDog/integrations-core/pull/2700))

## 3.1.0 / 2018-11-30

***Added***:

* Add option to set `stream` parameter on requests ([#2658](https://github.com/DataDog/integrations-core/pull/2658)) Thanks [syskill](https://github.com/syskill).
* Upgrade cryptography ([#2659](https://github.com/DataDog/integrations-core/pull/2659))
* Upgrade requests ([#2481](https://github.com/DataDog/integrations-core/pull/2481))
* Fix unicode handling on A6 ([#2435](https://github.com/DataDog/integrations-core/pull/2435))
* Validate that the url starts with the scheme ([#2393](https://github.com/DataDog/integrations-core/pull/2393))

***Fixed***:

* Use raw string literals when \ is present ([#2465](https://github.com/DataDog/integrations-core/pull/2465))

## 3.0.0 / 2018-10-12 / Agent 6.6.0

***Changed***:

* Refactoring: isolate config parsing ([#2321](https://github.com/DataDog/integrations-core/pull/2321))

***Added***:

* Handle SSL exception and send a DOWN service check status ([#2332](https://github.com/DataDog/integrations-core/pull/2332))

## 2.4.0 / 2018-10-01

***Added***:

* Allow configuring cert expiration time in seconds ([#2290](https://github.com/DataDog/integrations-core/pull/2290))

***Fixed***:

* Fix fetching ca_certs from init_config ([#2318](https://github.com/DataDog/integrations-core/pull/2318))

## 2.3.0 / 2018-09-04 / Agent 6.5.0

***Added***:

* support NTLM auth ([#1812](https://github.com/DataDog/integrations-core/pull/1812))

***Fixed***:

* Update cryptography to 2.3 ([#1927](https://github.com/DataDog/integrations-core/pull/1927))
* fix link in config option description ([#1865](https://github.com/DataDog/integrations-core/pull/1865))
* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 2.2.0 / 2018-06-20 / Agent 6.3.1

***Fixed***:

* Add support client auth for http check cert expiration. ([#1754](https://github.com/DataDog/integrations-core/pull/1754))
* Check will now send data with PUT, DELETE, and PATCH methods--not just POST ([#1718](https://github.com/DataDog/integrations-core/pull/1718))

## 2.1.0 / 2018-06-06

***Changed***:

* Emit a warning if disable_ssl_validation is unset ([#1517](https://github.com/DataDog/integrations-core/pull/1517))

***Added***:

* Allow users to disable matching hostnames verification in ssl cert verification ([#1519](https://github.com/DataDog/integrations-core/pull/1519))

***Fixed***:

* fixes AttributeError when running on 6.2.1 ([#1617](https://github.com/DataDog/integrations-core/pull/1617))
* Suppress InsecureRequestWarning for urllib3 for http_check ([#1574](https://github.com/DataDog/integrations-core/pull/1574))

## 2.0.1 / 2018-05-11

***Fixed***:

* Properly detect default certificate file for all supported Platforms ([#1340](https://github)com/DataDog/integrations-core/pull/1340)

## 2.0.0 / 2018-03-23

***Deprecated***:

* Remove the `skip_event` option from the check ([#1054](https://github)com/DataDog/integrations-core/pull/1054)

***Fixed***:

* Make import of default certificate file relative rather than absolute
* Fixes loading problem on Windows, and/or allows check to be installed in other location

## 1.4.0 / 2018-02-13

***Added***:

* begin deprecation of `no_proxy` config flag in favor of `skip_proxy` ([#1057](https://github.com/DataDog/integrations-core/pull/1057))

## 1.3.1 / 2018-01-17

***Fixed***:

* Use lowercase in an `if statement` for a user defined HTTP method.

## 1.3.0 / 2018-01-10

***Added***:

* Report http connect status as metrics (#659)
* Add configurable ssl server name for cert expiration check. See[#905](https://github.com/DataDog/integrations-core/pull/905).

***Fixed***:

* User-defined "url" tag replaces default "url" tag. See[#301](https://github.com/DataDog/integrations-core/pull/301). (Thanks [@colinmollenhour](https://github.com/colinmollenhour))

## 1.2.0 / 2017-10-10

***Added***:

* Add support for client side certificate. See[#688](https://github.com/DataDog/integrations-core/issues/688). (Thanks [@xkrt](https://github.com/xkrt))
* Make tornado optional ([#758](https://github.com/DataDog/integrations-core/issues/758))

## 1.1.2 / 2017-08-28

***Added***:

* Improved logging ([#652](https://github.com/DataDog/integrations-core/issues/652))

## 1.1.1 / 2017-07-18

***Fixed***:

* Fix response tuple arity in SSL certificate check. See[#461](https://github.com/DataDog/integrations-core/issues/461).

## 1.1.0 / 2017-06-05

***Added***:

* Add support for SOAP requests ([#328](https://github.com/DataDog/integrations-core/issues/328))
* Add gauge metric for ssl days left ([#249](https://github.com/DataDog/integrations-core/issues/249))

## 1.0.0 / 2017-03-22

***Added***:

* adds http_check integration.

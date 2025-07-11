# CHANGELOG - Vault

<!-- towncrier release notes start -->

## 7.0.0 / 2025-07-10

***Changed***:

* Bump datadog_checks_base to 37.16.0 ([#20711](https://github.com/DataDog/integrations-core/pull/20711))

## 6.1.0 / 2025-01-16 / Agent 7.63.0

***Added***:

* Add `tls_ciphers` param to integration ([#19334](https://github.com/DataDog/integrations-core/pull/19334))

## 6.0.0 / 2024-10-04 / Agent 7.59.0

***Removed***:

* Remove support for Python 2. ([#18580](https://github.com/DataDog/integrations-core/pull/18580))

***Fixed***:

* Bump the version of datadog-checks-base to 37.0.0 ([#18617](https://github.com/DataDog/integrations-core/pull/18617))

## 5.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))

## 4.2.1 / 2024-07-05 / Agent 7.55.0

***Fixed***:

* Update config model names ([#17802](https://github.com/DataDog/integrations-core/pull/17802))

## 4.2.0 / 2024-05-31

***Added***:

* Add additional documented Vault metrics ([#17654](https://github.com/DataDog/integrations-core/pull/17654))

***Fixed***:

* Update the description for the `tls_ca_cert` config option to use `openssl rehash` instead of `c_rehash` ([#16981](https://github.com/DataDog/integrations-core/pull/16981))
* Do not fail if no tags are provided in the config ([#17598](https://github.com/DataDog/integrations-core/pull/17598))

## 4.1.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 4.0.1 / 2023-08-18 / Agent 7.48.0

***Fixed***:

* Add metrics for PKI tidy operations ([#14327](https://github.com/DataDog/integrations-core/pull/14327))

## 4.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 3.4.1 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 3.4.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))

***Fixed***:

* Update minimum datadog base package version ([#14463](https://github.com/DataDog/integrations-core/pull/14463))
* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))

## 3.3.3 / 2022-10-28 / Agent 7.41.0

***Fixed***:

* Ensure X-Vault-Request header is set to `true` on all requests ([#13006](https://github.com/DataDog/integrations-core/pull/13006))

## 3.3.2 / 2022-09-16 / Agent 7.40.0

***Fixed***:

* Do not use the `client_token` if `no_token` is true with the openmetrics v1 implementation ([#12776](https://github.com/DataDog/integrations-core/pull/12776))
* Use the `client_token` option with the openmetrics v2 implementation ([#12764](https://github.com/DataDog/integrations-core/pull/12764))

## 3.3.1 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Properly read `collect_secondary_dr` and improve code readability ([#12435](https://github.com/DataDog/integrations-core/pull/12435))

## 3.3.0 / 2022-06-01 / Agent 7.38.0

***Added***:

* Add config option to collect from secondary replication mode ([#12099](https://github.com/DataDog/integrations-core/pull/12099))

***Fixed***:

* Ensure vault_wal_gc_total is collected as gauge ([#12036](https://github.com/DataDog/integrations-core/pull/12036))

## 3.2.1 / 2022-05-18 / Agent 7.37.0

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))

## 3.2.0 / 2022-05-11

***Added***:

* Add `vault.replication.wal.gc.*` metrics ([#11984](https://github.com/DataDog/integrations-core/pull/11984))

***Fixed***:

* Fix metric naming ([#11847](https://github.com/DataDog/integrations-core/pull/11847))

## 3.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 3.0.2 / 2022-02-23 / Agent 7.35.0

***Fixed***:

* Add OpenMetrics V2 service check to Vault ([#11558](https://github.com/DataDog/integrations-core/pull/11558))

## 3.0.1 / 2022-02-19

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 3.0.0 / 2022-02-16

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11453](https://github.com/DataDog/integrations-core/pull/11453))
* Add support for OpenMetrics v2 ([#11293](https://github.com/DataDog/integrations-core/pull/11293))

## 2.17.1 / 2022-01-08 / Agent 7.34.0

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 2.17.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 2.16.0 / 2021-09-09

***Added***:

* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))
* Update vault metrics ([#9953](https://github.com/DataDog/integrations-core/pull/9953))

## 2.15.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Use `display_default` as a fallback for `default` when validating config models ([#9739](https://github.com/DataDog/integrations-core/pull/9739))

## 2.14.0 / 2021-07-20

***Added***:

* Add new vault metrics ([#9728](https://github.com/DataDog/integrations-core/pull/9728))
* Add Vault route metrics to be fetched from the Prometheus endpoint ([#9612](https://github.com/DataDog/integrations-core/pull/9612)) Thanks [mdgreenfield](https://github.com/mdgreenfield).
* Add newer Hashicorp Vault metrics ([#9641](https://github.com/DataDog/integrations-core/pull/9641)) Thanks [mdgreenfield](https://github.com/mdgreenfield).

## 2.13.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Add runtime configuration validation ([#9002](https://github.com/DataDog/integrations-core/pull/9002))

## 2.12.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Add Additional Vault Route Metrics ([#8761](https://github.com/DataDog/integrations-core/pull/8761))

***Fixed***:

* Fix refactored imports ([#9136](https://github.com/DataDog/integrations-core/pull/9136))
* Bump minimum base package ([#9107](https://github.com/DataDog/integrations-core/pull/9107))

## 2.11.0 / 2021-03-07 / Agent 7.27.0

***Added***:

* Rename cluster_name tag to vault_cluster ([#8577](https://github.com/DataDog/integrations-core/pull/8577))

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 2.10.0 / 2020-12-11 / Agent 7.25.0

***Added***:

* Add new Vault 1.5+ metrics ([#8031](https://github.com/DataDog/integrations-core/pull/8031))

## 2.9.1 / 2020-11-04 / Agent 7.24.0

***Fixed***:

* Fix secondary mode detection logic ([#7926](https://github.com/DataDog/integrations-core/pull/7926))

## 2.9.0 / 2020-10-21

***Added***:

* Detect replication DR secondary mode and skip Prometheus metric collection ([#7825](https://github.com/DataDog/integrations-core/pull/7825))

## 2.8.0 / 2020-10-13

***Added***:

* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))
* [doc] Add encoding in log config sample ([#7708](https://github.com/DataDog/integrations-core/pull/7708))

***Fixed***:

* Fix vault raft storage metric name ([#6622](https://github.com/DataDog/integrations-core/pull/6622)) Thanks [tgermain](https://github.com/tgermain).

## 2.7.0 / 2020-09-21 / Agent 7.23.0

***Added***:

* Add RequestsWrapper option to support UTF-8 for basic auth ([#7441](https://github.com/DataDog/integrations-core/pull/7441))

***Fixed***:

* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))
* Update proxy section in conf.yaml ([#7336](https://github.com/DataDog/integrations-core/pull/7336))

## 2.6.1 / 2020-08-10 / Agent 7.22.0

***Fixed***:

* Update logs config service field to optional ([#7209](https://github.com/DataDog/integrations-core/pull/7209))
* DOCS-838 Template wording ([#7038](https://github.com/DataDog/integrations-core/pull/7038))
* Update ntlm_domain example ([#7118](https://github.com/DataDog/integrations-core/pull/7118))

## 2.6.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Add note about warning concurrency ([#6967](https://github.com/DataDog/integrations-core/pull/6967))

***Fixed***:

* Fix template specs typos ([#6912](https://github.com/DataDog/integrations-core/pull/6912))

## 2.5.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 2.4.0 / 2020-05-04

***Added***:

* Add Raft storage backend metrics ([#6492](https://github.com/DataDog/integrations-core/pull/6492)) Thanks [fabienrenaud](https://github.com/fabienrenaud).

## 2.3.2 / 2020-05-04 / Agent 7.19.2

***Fixed***:

* Fixed infinite stream of Vault leader detection events ([#6552](https://github.com/DataDog/integrations-core/pull/6552)) Thanks [fabienrenaud](https://github.com/fabienrenaud).

## 2.3.1 / 2020-04-07 / Agent 7.19.0

***Fixed***:

* Add `kerberos_cache` to HTTP config options ([#6279](https://github.com/DataDog/integrations-core/pull/6279))

## 2.3.0 / 2020-04-04

***Added***:

* Add option to set SNI hostname via the `Host` header for RequestsWrapper ([#5833](https://github.com/DataDog/integrations-core/pull/5833))

***Fixed***:

* Remove logs sourcecategory ([#6121](https://github.com/DataDog/integrations-core/pull/6121))
* Fix event submission on leader change ([#6039](https://github.com/DataDog/integrations-core/pull/6039))

## 2.2.1 / 2020-02-25 / Agent 7.18.0

***Fixed***:

* Update datadog_checks_base dependencies ([#5846](https://github.com/DataDog/integrations-core/pull/5846))

## 2.2.0 / 2020-02-22

***Added***:

* Add `service` option to default configuration ([#5805](https://github.com/DataDog/integrations-core/pull/5805))
* Add missing vault summary metric ([#5670](https://github.com/DataDog/integrations-core/pull/5670))

## 2.1.2 / 2020-01-24 / Agent 7.17.0

***Fixed***:

* Send summary count metrics as a count ([#5538](https://github.com/DataDog/integrations-core/pull/5538))

## 2.1.1 / 2020-01-13

***Fixed***:

* Fix http handler ([#5434](https://github.com/DataDog/integrations-core/pull/5434))

## 2.1.0 / 2020-01-09

***Added***:

* Add support for metric collection without a token ([#5424](https://github.com/DataDog/integrations-core/pull/5424))
* Make OpenMetrics use the RequestsWrapper ([#5414](https://github.com/DataDog/integrations-core/pull/5414))

## 2.0.0 / 2019-12-21

***Changed***:

* Collect prometheus metrics if a client token is available ([#5177](https://github.com/DataDog/integrations-core/pull/5177))

## 1.7.1 / 2019-10-21 / Agent 6.15.0

***Fixed***:

* Fix is_leader when vault sealed ([#4838](https://github.com/DataDog/integrations-core/pull/4838))

## 1.7.0 / 2019-10-18

***Added***:

* Allows certain expected HTTP error status_codes for the `/sys/health` endpoint ([#4745](https://github.com/DataDog/integrations-core/pull/4745))

## 1.6.0 / 2019-10-07

***Added***:

* Add option to override KRB5CCNAME env var ([#4578](https://github.com/DataDog/integrations-core/pull/4578))

***Fixed***:

* Fix crash in HA mode ([#4698](https://github.com/DataDog/integrations-core/pull/4698))

## 1.5.0 / 2019-08-24 / Agent 6.14.0

***Added***:

* Add requests wrapper to vault ([#4259](https://github.com/DataDog/integrations-core/pull/4259))

## 1.4.1 / 2019-07-31

***Fixed***:

* Submit critical service check with 500 server errors ([#4242](https://github.com/DataDog/integrations-core/pull/4242))

## 1.4.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3580](https://github.com/DataDog/integrations-core/pull/3580))

## 1.3.1 / 2019-01-04 / Agent 6.9.0

***Fixed***:

* Fix unsupported API version fallback ([#2793][1])

## 1.3.0 / 2018-11-30 / Agent 6.8.0

***Added***:

* Support custom certificates ([#2657][2]) Thanks [eedwards-sk][3].

## 1.2.0 / 2018-08-15 / Agent 6.5.0

***Added***:

* Add is_leader metric ([#2057][4])

## 1.1.0 / 2018-08-08

***Changed***:

* Add data files to the wheel package ([#1727][6])

***Added***:

* Add option to disable urllib3 warnings ([#2009][5])

## 1.0.0 / 2018-06-19

***Added***:

* Add Vault integration ([#1759][7])

[1]: https://github.com/DataDog/integrations-core/pull/2793
[2]: https://github.com/DataDog/integrations-core/pull/2657
[3]: https://github.com/eedwards-sk
[4]: https://github.com/DataDog/integrations-core/pull/2057
[5]: https://github.com/DataDog/integrations-core/pull/2009
[6]: https://github.com/DataDog/integrations-core/pull/1727
[7]: https://github.com/DataDog/integrations-core/pull/1759

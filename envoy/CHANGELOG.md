# CHANGELOG - Envoy

<!-- towncrier release notes start -->

## 3.4.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Add additional cluster and listener metrics for OpenMetrics version of check ([#16649](https://github.com/DataDog/integrations-core/pull/16649))
* Add connection limit metrics for envoy ([#16718](https://github.com/DataDog/integrations-core/pull/16718))
* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

## 3.3.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Add local rate limit metrics ([#16313](https://github.com/DataDog/integrations-core/pull/16313))
* Add new RBAC metrics in Legacy check ([#16432](https://github.com/DataDog/integrations-core/pull/16432))
* Add connect state metric for OpenmetricsV2 and add way to collect shadow prefixes in legacy check for RBAC metrics ([#16453](https://github.com/DataDog/integrations-core/pull/16453))
* Add a `endpoint` tag to every metric in the legacy version of the check ([#16478](https://github.com/DataDog/integrations-core/pull/16478))

## 3.2.0 / 2023-11-10 / Agent 7.50.0

***Added***:

* Add rbac metrics ([#16165](https://github.com/DataDog/integrations-core/pull/16165))

## 3.1.0 / 2023-09-29 / Agent 7.49.0

***Added***:

* Add [TCP proxy statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/listeners/network_filters/tcp_proxy_filter#statistics) ([#15704](https://github.com/DataDog/integrations-core/pull/15704))

## 3.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 2.6.1 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Disable server info and version collection when collect_server_info is false ([#14610](https://github.com/DataDog/integrations-core/pull/14610))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 2.6.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))
* Add GRPC access log metrics ([#13932](https://github.com/DataDog/integrations-core/pull/13932))

***Fixed***:

* Update minimum datadog base package version ([#14463](https://github.com/DataDog/integrations-core/pull/14463))
* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))

## 2.5.0 / 2023-03-03 / Agent 7.44.0

***Added***:

* Parse and add the tag `stat_prefix` to `ext_authz` metrics if possible ([#13930](https://github.com/DataDog/integrations-core/pull/13930))

***Fixed***:

* Add missing metrics ([#14036](https://github.com/DataDog/integrations-core/pull/14036) and [#14088](https://github.com/DataDog/integrations-core/pull/14088))

## 2.4.1 / 2023-01-20 / Agent 7.43.0

***Fixed***:

* Fix metric mapping of counter metrics in the Openmetrics V2 version of the check ([#13573](https://github.com/DataDog/integrations-core/pull/13573))

## 2.4.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))
* [Envoy] Support `envoy.cluster.outlier_detection.*` in OpenMetrics V2 ([#11860](https://github.com/DataDog/integrations-core/pull/11860))

## 2.3.1 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 2.3.0 / 2022-07-05 / Agent 7.38.0

***Added***:

* Add ext_authz and ratelimiter metrics to OpenMetrics implementation ([#12451](https://github.com/DataDog/integrations-core/pull/12451))

## 2.2.0 / 2022-06-27

***Added***:

* Add ext_authz metrics to envoy integration ([#12374](https://github.com/DataDog/integrations-core/pull/12374)) Thanks [Kaycell](https://github.com/Kaycell).

## 2.1.1 / 2022-05-18 / Agent 7.37.0

***Fixed***:

* Fix extra metrics description example ([#12043](https://github.com/DataDog/integrations-core/pull/12043))

## 2.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 2.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11345](https://github.com/DataDog/integrations-core/pull/11345))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 1.26.0 / 2022-01-08 / Agent 7.34.0

***Added***:

* Support Openmetrics metrics collection ([#10752](https://github.com/DataDog/integrations-core/pull/10752))

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 1.25.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Bump base package dependency ([#10218](https://github.com/DataDog/integrations-core/pull/10218))
* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 1.24.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Use `display_default` as a fallback for `default` when validating config models ([#9739](https://github.com/DataDog/integrations-core/pull/9739))

## 1.23.0 / 2021-06-17 / Agent 7.30.0

***Added***:

* Add v3 API metrics ([#9468](https://github.com/DataDog/integrations-core/pull/9468))
* Rename cluster_name tag to envoy_cluster ([#9430](https://github.com/DataDog/integrations-core/pull/9430))

## 1.22.0 / 2021-05-06 / Agent 7.29.0

***Added***:

* Add collect_server_info config option ([#9298](https://github.com/DataDog/integrations-core/pull/9298))
* Add missing Envoy HTTP router filter vhost metrics ([#8586](https://github.com/DataDog/integrations-core/pull/8586)) Thanks [csssuf](https://github.com/csssuf).

## 1.21.1 / 2021-04-20 / Agent 7.28.0

***Fixed***:

* Fix retry parsing when metric has multiple metric parts ([#9189](https://github.com/DataDog/integrations-core/pull/9189))

## 1.21.0 / 2021-04-09

***Added***:

* Add retry option when metric is not found ([#9120](https://github.com/DataDog/integrations-core/pull/9120))
* Add runtime configuration validation ([#8912](https://github.com/DataDog/integrations-core/pull/8912))

## 1.20.2 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.20.1 / 2021-01-25 / Agent 7.26.0

***Fixed***:

* Update check signature ([#8258](https://github.com/DataDog/integrations-core/pull/8258))

## 1.20.0 / 2020-10-31 / Agent 7.24.0

***Added***:

* Add newly documented metrics ([#7765](https://github.com/DataDog/integrations-core/pull/7765))
* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))

## 1.19.0 / 2020-10-07

***Added***:

* Add encoding in log config sample ([#7708](https://github.com/DataDog/integrations-core/pull/7708))

***Fixed***:

* Update Watchdog metrics ([#7740](https://github.com/DataDog/integrations-core/pull/7740))
* Properly handle a parsing edge case ([#7717](https://github.com/DataDog/integrations-core/pull/7717))

## 1.18.0 / 2020-09-21 / Agent 7.23.0

***Added***:

* Add RequestsWrapper option to support UTF-8 for basic auth ([#7441](https://github.com/DataDog/integrations-core/pull/7441))

***Fixed***:

* Do not render null defaults for config spec example consumer ([#7503](https://github.com/DataDog/integrations-core/pull/7503))
* Update proxy section in conf.yaml ([#7336](https://github.com/DataDog/integrations-core/pull/7336))

## 1.17.0 / 2020-08-10 / Agent 7.22.0

***Added***:

* envoy config specs ([#7157](https://github.com/DataDog/integrations-core/pull/7157))

***Fixed***:

* Update logs config service field to optional ([#7209](https://github.com/DataDog/integrations-core/pull/7209))
* DOCS-838 Template wording ([#7038](https://github.com/DataDog/integrations-core/pull/7038))
* Use inclusive naming ([#7156](https://github.com/DataDog/integrations-core/pull/7156))
* Update ntlm_domain example ([#7118](https://github.com/DataDog/integrations-core/pull/7118))

## 1.16.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Add note about warning concurrency ([#6967](https://github.com/DataDog/integrations-core/pull/6967))

## 1.15.2 / 2020-05-26 / Agent 7.20.0

***Fixed***:

* Handle server info for envoy <= 1.8 ([#6740](https://github.com/DataDog/integrations-core/pull/6740))

## 1.15.1 / 2020-05-19

***Fixed***:

* Safer metadata error handling ([#6685](https://github.com/DataDog/integrations-core/pull/6685))

## 1.15.0 / 2020-05-17

***Added***:

* Collect version metadata ([#6595](https://github.com/DataDog/integrations-core/pull/6595))
* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

***Fixed***:

* Fix style to account for new flake8 rules ([#6620](https://github.com/DataDog/integrations-core/pull/6620))

## 1.14.0 / 2020-04-04 / Agent 7.19.0

***Added***:

* Update doc about whitelist and blacklist ([#5875](https://github.com/DataDog/integrations-core/pull/5875))

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))
* Remove logs sourcecategory ([#6121](https://github.com/DataDog/integrations-core/pull/6121))

## 1.13.0 / 2020-02-22 / Agent 7.18.0

***Added***:

* Add support for more metrics in Envoy integration ([#5537](https://github.com/DataDog/integrations-core/pull/5537)) Thanks [csssuf](https://github.com/csssuf).

## 1.12.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 1.11.0 / 2019-12-02 / Agent 7.16.0

***Added***:

* Add new metrics for Redis ([#4946](https://github.com/DataDog/integrations-core/pull/4946)) Thanks [tony612](https://github.com/tony612).
* Add auth type to RequestsWrapper ([#4708](https://github.com/DataDog/integrations-core/pull/4708))

## 1.10.0 / 2019-10-11 / Agent 6.15.0

***Added***:

* Add xDS-related metrics ([#4634](https://github.com/DataDog/integrations-core/pull/4634)) Thanks [csssuf](https://github.com/csssuf).
* Add option to override KRB5CCNAME env var ([#4578](https://github.com/DataDog/integrations-core/pull/4578))

## 1.9.0 / 2019-08-24 / Agent 6.14.0

***Added***:

* Add RequestsWrapper to envoy ([#4120](https://github.com/DataDog/integrations-core/pull/4120))

## 1.8.0 / 2019-07-04 / Agent 6.13.0

***Added***:

* Add cluster.ssl metrics to Envoy integration ([#3976](https://github.com/DataDog/integrations-core/pull/3976)) Thanks [csssuf](https://github.com/csssuf).
* Add Envoy upstream_rq_completed cluster metrics ([#3955](https://github.com/DataDog/integrations-core/pull/3955)) Thanks [csssuf](https://github.com/csssuf).

## 1.7.0 / 2019-06-19

***Added***:

* Add more listener metrics ([#3922](https://github.com/DataDog/integrations-core/pull/3922))

## 1.6.0 / 2019-06-18

***Added***:

* Add logs config to envoy ([#3918](https://github.com/DataDog/integrations-core/pull/3918))

## 1.5.0 / 2019-03-29 / Agent 6.11.0

***Added***:

* Adhere to style ([#3366](https://github.com/DataDog/integrations-core/pull/3366))

## 1.4.0 / 2018-09-05 / Agent 6.5.0

***Changed***:

* Change order of precedence of whitelist and blacklist for pattern filtering ([#2174](https://github.com/DataDog/integrations-core/pull/2174))

## 1.3.0 / 2018-08-06

***Changed***:

* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

***Added***:

* Add ability to whitelist/blacklist metrics ([#1975](https://github.com/DataDog/integrations-core/pull/1975))

## 1.2.1 / 2018-06-14 / Agent 6.4.0

***Fixed***:

* properly send tags for histograms ([#1741](https://github.com/DataDog/integrations-core/pull/1741))

## 1.2.0 / 2018-06-07

***Added***:

* support histograms, fix count submission ([#1616](https://github.com/DataDog/integrations-core/pull/1616))

## 1.1.0 / 2018-05-11

***Added***:

* add newly-documented metrics. See #1326
* tags can now contain the dot metric delimiter itself. See #1404

## 1.0.0 / 2018-03-23

***Added***:

* add Envoy integration. See #1156

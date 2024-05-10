# CHANGELOG - gitlab

<!-- towncrier release notes start -->

## 7.3.0 / 2024-04-26

***Added***:

* Adds additional Geo metrics. *Note: Some metrics are only available depending on your Gitlab version: refer to the Metrics sub-section in Data Collected available in our [documentation](https://docs.datadoghq.com/integrations/gitlab/) to see the minimum required version (indicated within brackets). For instance, `gitlab.geo.group.wiki.repositories` requires at least `13.10`.* ([#17420](https://github.com/DataDog/integrations-core/pull/17420))

## 7.2.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Update the configuration file to include the new oauth options parameter ([#16835](https://github.com/DataDog/integrations-core/pull/16835))

***Fixed***:

* Remove the direct dependency to `protobuf` ([#16572](https://github.com/DataDog/integrations-core/pull/16572))

## 7.1.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 7.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 6.2.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 6.1.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))
* Add support for Gitaly metrics ([#14316](https://github.com/DataDog/integrations-core/pull/14316))

***Fixed***:

* Revert protobuf dependency update ([#14618](https://github.com/DataDog/integrations-core/pull/14618))
* Update dependencies ([#14594](https://github.com/DataDog/integrations-core/pull/14594))
* Refactor how we manage the namespaces ([#14462](https://github.com/DataDog/integrations-core/pull/14462))
* Update minimum datadog base package version ([#14463](https://github.com/DataDog/integrations-core/pull/14463))
* Deprecate `use_latest_spec` option ([#14446](https://github.com/DataDog/integrations-core/pull/14446))

## 6.0.2 / 2023-04-21 / Agent 7.45.0

***Fixed***:

* Collect the readiness service checks even if the readiness payload is malformed ([#14411](https://github.com/DataDog/integrations-core/pull/14411))

## 6.0.1 / 2023-04-19

***Fixed***:

* Fix Gitlab documentation in conf.yaml ([#14400](https://github.com/DataDog/integrations-core/pull/14400))
* Ensure the check runs correctly if no gitlab url is defined ([#14403](https://github.com/DataDog/integrations-core/pull/14403))

## 6.0.0 / 2023-04-14

***Changed***:

* Add support for OpenMetricsV2 ([#14273](https://github.com/DataDog/integrations-core/pull/14273))
* Set the `send_distribution_sums_as_monotonic` option to `true` by default ([#14290](https://github.com/DataDog/integrations-core/pull/14290))

***Added***:

* Add new service checks ([#14311](https://github.com/DataDog/integrations-core/pull/14311))

***Fixed***:

* Fix the `health_service_check` config option ([#14288](https://github.com/DataDog/integrations-core/pull/14288))
* Add the `prometheus_endpoint` option to the models ([#14264](https://github.com/DataDog/integrations-core/pull/14264))
* Add missing tags when the service check is critical ([#14262](https://github.com/DataDog/integrations-core/pull/14262))

## 5.3.2 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Update protobuf ([#13262](https://github.com/DataDog/integrations-core/pull/13262))

## 5.3.1 / 2022-11-07 / Agent 7.40.1

***Fixed***:

* Bump protobuf version to 3.20.2 ([#13269](https://github.com/DataDog/integrations-core/pull/13269))

## 5.3.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Update HTTP config spec templates ([#12890](https://github.com/DataDog/integrations-core/pull/12890))

***Fixed***:

* Updates GitLab URL documentation ([#12683](https://github.com/DataDog/integrations-core/pull/12683))

## 5.2.3 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 5.2.2 / 2022-06-30 / Agent 7.38.0

***Fixed***:

* Fix default config value ([#12429](https://github.com/DataDog/integrations-core/pull/12429))

## 5.2.1 / 2022-06-27

***Fixed***:

* Change default value for the send_monotonic_counter to false ([#12022](https://github.com/DataDog/integrations-core/pull/12022))

## 5.2.0 / 2022-05-15 / Agent 7.37.0

***Added***:

* Support dynamic bearer tokens (Bound Service Account Token Volume) ([#11915](https://github.com/DataDog/integrations-core/pull/11915))

***Fixed***:

* Upgrade dependencies ([#11958](https://github.com/DataDog/integrations-core/pull/11958))

## 5.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 5.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11353](https://github.com/DataDog/integrations-core/pull/11353))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 4.7.3 / 2022-01-21 / Agent 7.34.0

***Fixed***:

* Fix license header dates in autogenerated files ([#11187](https://github.com/DataDog/integrations-core/pull/11187))

## 4.7.2 / 2022-01-18

***Fixed***:

* Fix the type of `bearer_token_auth` ([#11144](https://github.com/DataDog/integrations-core/pull/11144))

## 4.7.1 / 2022-01-08

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 4.7.0 / 2021-11-13 / Agent 7.33.0

***Added***:

* Document new include_labels option ([#10617](https://github.com/DataDog/integrations-core/pull/10617))
* Document new use_process_start_time option ([#10601](https://github.com/DataDog/integrations-core/pull/10601))

## 4.6.1 / 2021-10-05 / Agent 7.32.0

***Fixed***:

* Fix config example ([#10338](https://github.com/DataDog/integrations-core/pull/10338))

## 4.6.0 / 2021-10-04

***Added***:

* Add runtime configuration validation ([#8918](https://github.com/DataDog/integrations-core/pull/8918))
* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 4.5.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Support "ignore_tags" configuration ([#9392](https://github.com/DataDog/integrations-core/pull/9392))

## 4.4.2 / 2021-03-07 / Agent 7.27.0

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 4.4.1 / 2021-01-25 / Agent 7.26.0

***Fixed***:

* Update prometheus_metrics_prefix documentation ([#8236](https://github.com/DataDog/integrations-core/pull/8236))
* Update check signature ([#8248](https://github.com/DataDog/integrations-core/pull/8248))

## 4.4.0 / 2020-10-31 / Agent 7.24.0

***Added***:

* Sync openmetrics config specs with new option ignore_metrics_by_labels ([#7823](https://github.com/DataDog/integrations-core/pull/7823))
* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))
* [doc] Add encoding in log config sample ([#7708](https://github.com/DataDog/integrations-core/pull/7708))

## 4.3.0 / 2020-09-21 / Agent 7.23.0

***Added***:

* Add new gitlab v13 metrics ([#7561](https://github.com/DataDog/integrations-core/pull/7561))
* Add RequestsWrapper option to support UTF-8 for basic auth ([#7441](https://github.com/DataDog/integrations-core/pull/7441))

***Fixed***:

* Update proxy section in conf.yaml ([#7336](https://github.com/DataDog/integrations-core/pull/7336))

## 4.2.0 / 2020-08-10 / Agent 7.22.0

***Added***:

* Support "*" wildcard in type_overrides configuration ([#7071](https://github.com/DataDog/integrations-core/pull/7071))

***Fixed***:

* Update logs config service field to optional ([#7209](https://github.com/DataDog/integrations-core/pull/7209))
* DOCS-838 Template wording ([#7038](https://github.com/DataDog/integrations-core/pull/7038))
* Update ntlm_domain example ([#7118](https://github.com/DataDog/integrations-core/pull/7118))

## 4.1.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Add note about warning concurrency ([#6967](https://github.com/DataDog/integrations-core/pull/6967))

***Fixed***:

* Fix template specs typos ([#6912](https://github.com/DataDog/integrations-core/pull/6912))

## 4.0.0 / 2020-05-17 / Agent 7.20.0

***Changed***:

* Remove duplicates in metadata and assert metrics with metadata ([#6516](https://github.com/DataDog/integrations-core/pull/6516))

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))
* Add config spec ([#6151](https://github.com/DataDog/integrations-core/pull/6151))

## 3.0.0 / 2020-04-04 / Agent 7.19.0

***Changed***:

* Remap gitlab metrics ([#6150](https://github.com/DataDog/integrations-core/pull/6150))
* Gitlab revamp ([#5971](https://github.com/DataDog/integrations-core/pull/5971))

***Added***:

* Add new gitlab metrics ([#6166](https://github.com/DataDog/integrations-core/pull/6166))
* Include gitlab host and port tag for all metrics ([#6177](https://github.com/DataDog/integrations-core/pull/6177))
* Add version metadata ([#5786](https://github.com/DataDog/integrations-core/pull/5786))

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))
* Remove logs sourcecategory ([#6121](https://github.com/DataDog/integrations-core/pull/6121))

## 2.8.1 / 2020-02-22 / Agent 7.18.0

***Fixed***:

* Fix metric validation ([#5581](https://github.com/DataDog/integrations-core/pull/5581))

## 2.8.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))

## 2.7.0 / 2019-12-02 / Agent 7.16.0

***Added***:

* Add auth type to RequestsWrapper ([#4708](https://github.com/DataDog/integrations-core/pull/4708))

## 2.6.1 / 2019-10-17 / Agent 6.15.0

***Fixed***:

* Add missing go_memstats_stack_sys_bytes metric in conf file ([#4800](https://github.com/DataDog/integrations-core/pull/4800))

## 2.6.0 / 2019-10-11

***Added***:

* Add option to override KRB5CCNAME env var ([#4578](https://github.com/DataDog/integrations-core/pull/4578))

## 2.5.1 / 2019-08-30 / Agent 6.14.0

***Fixed***:

* Update class signature to support the RequestsWrapper ([#4469](https://github.com/DataDog/integrations-core/pull/4469))

## 2.5.0 / 2019-08-24

***Added***:

* Add requests wrapper to gitlab ([#4216](https://github.com/DataDog/integrations-core/pull/4216))

## 2.4.0 / 2019-07-04 / Agent 6.13.0

***Added***:

* Add logs ([#3948](https://github.com/DataDog/integrations-core/pull/3948))

## 2.3.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3509](https://github.com/DataDog/integrations-core/pull/3509))

## 2.2.0 / 2019-03-29 / Agent 6.11.0

***Added***:

* Upgrade protobuf to 3.7.0 ([#3272](https://github.com/DataDog/integrations-core/pull/3272))

## 2.1.0 / 2019-01-04 / Agent 6.9.0

***Added***:

* Support Python 3 ([#2751][1])

## 2.0.0 / 2018-10-12 / Agent 6.6.0

***Changed***:

* Update gitlab to use the new OpenMetricsBaseCheck ([#1977][2])

## 1.2.0 / 2018-09-04 / Agent 6.5.0

***Added***:

* Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default ([#2093][3])

***Fixed***:

* Add data files to the wheel package ([#1727][4])

## 1.1.0 / 2018-03-23

***Added***:

* Add support for instance level checks in service check.

## 1.0.0 / 2018-01-10

***Added***:

* Add integration for Gitlab.

[1]: https://github.com/DataDog/integrations-core/pull/2751
[2]: https://github.com/DataDog/integrations-core/pull/1977
[3]: https://github.com/DataDog/integrations-core/pull/2093
[4]: https://github.com/DataDog/integrations-core/pull/1727

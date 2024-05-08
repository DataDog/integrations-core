# CHANGELOG - Openstack_controller

<!-- towncrier release notes start -->

## 6.5.0 / 2024-04-26

***Added***:

* Added new cinder metrics ([#17422](https://github.com/DataDog/integrations-core/pull/17422))

## 6.4.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Add pagination support for network networks ([#16930](https://github.com/DataDog/integrations-core/pull/16930))
* Update dependencies ([#16963](https://github.com/DataDog/integrations-core/pull/16963))
* Add pagination support for baremetal conductors ([#17026](https://github.com/DataDog/integrations-core/pull/17026))
* Add pagination support for loadbalancers ([#17100](https://github.com/DataDog/integrations-core/pull/17100))
* Add pagination support for listeners ([#17120](https://github.com/DataDog/integrations-core/pull/17120))
* Add pagination support for pools ([#17140](https://github.com/DataDog/integrations-core/pull/17140))
* Add pagination support for amphorae ([#17150](https://github.com/DataDog/integrations-core/pull/17150))

## 6.3.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Bump `openstacksdk` version to 2.0.0 ([#16549](https://github.com/DataDog/integrations-core/pull/16549))
* Update dependencies ([#16788](https://github.com/DataDog/integrations-core/pull/16788))

***Fixed***:

* Add support for pagination for servers details ([#16529](https://github.com/DataDog/integrations-core/pull/16529))

## 6.2.1 / 2024-01-10 / Agent 7.51.0

***Fixed***:

* Fix ironic nodes pagination logic ([#16566](https://github.com/DataDog/integrations-core/pull/16566))

## 6.2.0 / 2024-01-05

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Add pagination support for ironic nodes endpoint ([#16400](https://github.com/DataDog/integrations-core/pull/16400))

***Fixed***:

* Use params arg over manual url encoding for requests with query params ([#16200](https://github.com/DataDog/integrations-core/pull/16200))

## 6.1.0 / 2023-11-10 / Agent 7.50.0

***Added***:

* Add support for glance component. ([#16186](https://github.com/DataDog/integrations-core/pull/16186))

## 6.0.0 / 2023-11-07

***Changed***:

* Refactor integration and add support for Ironic and Octavia components. ([#15918](https://github.com/DataDog/integrations-core/pull/15918))

## 5.0.0 / 2023-09-29 / Agent 7.49.0

***Changed***:

* Upgrade to openstacksdk version 1.5.0 ([#15919](https://github.com/DataDog/integrations-core/pull/15919))

## 4.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 3.1.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Add runtime configuration validation ([#14362](https://github.com/DataDog/integrations-core/pull/14362))

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 3.0.0 / 2023-03-07 / Agent 7.44.0

***Changed***:

* Upgrade openstacksdk dependency and drop py2 ([#14109](https://github.com/DataDog/integrations-core/pull/14109))

## 2.1.4 / 2023-03-03

***Fixed***:

* Standardize log messages ([#14072](https://github.com/DataDog/integrations-core/pull/14072))

## 2.1.3 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))
* Pin the keystoneauth1 version for py2 ([#13445](https://github.com/DataDog/integrations-core/pull/13445))

## 2.1.2 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 2.1.1 / 2022-06-17 / Agent 7.38.0

***Fixed***:

* Attempt to use token from project scope with an admin role ([#12135](https://github.com/DataDog/integrations-core/pull/12135))

## 2.1.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Remove outdated warning in the description for the `tls_ignore_warning` option ([#11591](https://github.com/DataDog/integrations-core/pull/11591))

## 2.0.0 / 2022-02-19 / Agent 7.35.0

***Changed***:

* Add tls_protocols_allowed option documentation ([#11251](https://github.com/DataDog/integrations-core/pull/11251))

***Added***:

* Add `pyproject.toml` file ([#11409](https://github.com/DataDog/integrations-core/pull/11409))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 1.13.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Update dependencies ([#10258](https://github.com/DataDog/integrations-core/pull/10258))
* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))

***Fixed***:

* Fix the description of the `allow_redirects` HTTP option ([#10195](https://github.com/DataDog/integrations-core/pull/10195))

## 1.12.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Bump openstacksdk and add missing metrics ([#9861](https://github.com/DataDog/integrations-core/pull/9861))

***Fixed***:

* Do not leak password on logs ([#9637](https://github.com/DataDog/integrations-core/pull/9637))

## 1.11.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Openstack controller log support ([#9115](https://github.com/DataDog/integrations-core/pull/9115))

***Fixed***:

* Fix refactored imports ([#9136](https://github.com/DataDog/integrations-core/pull/9136))
* Add config spec for Openstack Controller ([#9092](https://github.com/DataDog/integrations-core/pull/9092))

## 1.10.3 / 2021-02-11 / Agent 7.27.0

***Fixed***:

* Remove SimpleApi cache ([#8583](https://github.com/DataDog/integrations-core/pull/8583))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 1.10.2 / 2020-09-21 / Agent 7.23.0

***Fixed***:

* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 1.10.1 / 2020-08-10 / Agent 7.22.0

***Fixed***:

* Update ntlm_domain example ([#7118](https://github.com/DataDog/integrations-core/pull/7118))

## 1.10.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Add note about warning concurrency ([#6967](https://github.com/DataDog/integrations-core/pull/6967))

## 1.9.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.8.1 / 2020-02-25 / Agent 7.18.0

***Fixed***:

* Bump datadog_checks_base dependency to 11.0.0 ([#5838](https://github.com/DataDog/integrations-core/pull/5838))

## 1.8.0 / 2020-02-22

***Added***:

* Refactor traced decorator and remove wrapt import ([#5586](https://github.com/DataDog/integrations-core/pull/5586))

## 1.7.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 1.6.0 / 2019-10-11 / Agent 6.15.0

***Added***:

* Add option to override KRB5CCNAME env var ([#4578](https://github.com/DataDog/integrations-core/pull/4578))

## 1.5.1 / 2019-08-30 / Agent 6.14.0

***Fixed***:

* Update class signature to support the RequestsWrapper ([#4469](https://github.com/DataDog/integrations-core/pull/4469))

## 1.5.0 / 2019-08-24

***Added***:

* Add requests wrapper to openstack_controller ([#4365](https://github.com/DataDog/integrations-core/pull/4365))
* Deployment environment with Terraform ([#4039](https://github.com/DataDog/integrations-core/pull/4039))

## 1.4.0 / 2019-07-12 / Agent 6.13.0

***Added***:

* Retrieve floating IPs from network quotas ([#4079](https://github.com/DataDog/integrations-core/pull/4079))

## 1.3.0 / 2019-07-09

***Added***:

* Make keystone_server_url config optional in openstack_controller config ([#3920](https://github.com/DataDog/integrations-core/pull/3920))
* Openstack: introduce artificial metric in controller to distinguish from legacy integration ([#4036](https://github.com/DataDog/integrations-core/pull/4036))

## 1.2.1 / 2019-06-01 / Agent 6.12.0

***Fixed***:

* Fix code style ([#3838](https://github.com/DataDog/integrations-core/pull/3838))
* Sanitize external host tags ([#3792](https://github.com/DataDog/integrations-core/pull/3792))

## 1.2.0 / 2019-05-14

***Added***:

* Adhere to code style ([#3551](https://github.com/DataDog/integrations-core/pull/3551))

## 1.1.2 / 2019-04-15

***Fixed***:

* Get details for both private and public flavors ([#3621](https://github.com/DataDog/integrations-core/pull/3621))

## 1.1.1 / 2019-03-21 / Agent 6.11.0

***Fixed***:

* Fix issue with exception handling preventing re-authentication in case of token expiration ([#3321](https://github.com/DataDog/integrations-core/pull/3321))

## 1.1.0 / 2019-03-15

***Added***:

* Add project tags to hypervisor metrics ([#3277](https://github.com/DataDog/integrations-core/pull/3277))
* Add openstacksdk option to openstack_controller ([#3109](https://github.com/DataDog/integrations-core/pull/3109))

***Fixed***:

* Fix pagination logic when making request to get servers/flavors details ([#3301](https://github.com/DataDog/integrations-core/pull/3301))
* Refactor openstack_controller check api and back caches ([#3142](https://github.com/DataDog/integrations-core/pull/3142))

## 1.0.1 / 2019-02-18 / Agent 6.10.0

***Fixed***:

* Refactor openstack_controller check cache ([#3120](https://github.com/DataDog/integrations-core/pull/3120))

## 1.0.0 / 2019-02-04

***Added***:

* OpenStack Controller ([#2496](https://github.com/DataDog/integrations-core/pull/2496))

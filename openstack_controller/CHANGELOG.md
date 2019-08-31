# CHANGELOG - Openstack_controller

## 1.5.1 / 2019-08-30

* [Fixed] Update class signature to support the RequestsWrapper. See [#4469](https://github.com/DataDog/integrations-core/pull/4469).

## 1.5.0 / 2019-08-24

* [Added] Add requests wrapper to openstack_controller. See [#4365](https://github.com/DataDog/integrations-core/pull/4365).
* [Added] Deployment environment with Terraform. See [#4039](https://github.com/DataDog/integrations-core/pull/4039).

## 1.4.0 / 2019-07-12

* [Added] Retrieve floating IPs from network quotas. See [#4079](https://github.com/DataDog/integrations-core/pull/4079).

## 1.3.0 / 2019-07-09

* [Added] Make keystone_server_url config optional in openstack_controller config. See [#3920](https://github.com/DataDog/integrations-core/pull/3920).
* [Added] Openstack: introduce artificial metric in controller to distinguish from legacy integration. See [#4036](https://github.com/DataDog/integrations-core/pull/4036).

## 1.2.1 / 2019-06-01

* [Fixed] Fix code style. See [#3838](https://github.com/DataDog/integrations-core/pull/3838).
* [Fixed] Sanitize external host tags. See [#3792](https://github.com/DataDog/integrations-core/pull/3792).

## 1.2.0 / 2019-05-14

* [Added] Adhere to code style. See [#3551](https://github.com/DataDog/integrations-core/pull/3551).

## 1.1.2 / 2019-04-15

* [Fixed] Get details for both private and public flavors. See [#3621](https://github.com/DataDog/integrations-core/pull/3621).

## 1.1.1 / 2019-03-21

* [Fixed] Fix issue with exception handling preventing re-authentication in case of token expiration. See [#3321](https://github.com/DataDog/integrations-core/pull/3321).

## 1.1.0 / 2019-03-15

* [Added] Add project tags to hypervisor metrics. See [#3277](https://github.com/DataDog/integrations-core/pull/3277).
* [Fixed] Fix pagination logic when making request to get servers/flavors details. See [#3301](https://github.com/DataDog/integrations-core/pull/3301).
* [Added] Add openstacksdk option to openstack_controller. See [#3109](https://github.com/DataDog/integrations-core/pull/3109).
* [Fixed] Refactor openstack_controller check api and back caches. See [#3142](https://github.com/DataDog/integrations-core/pull/3142).

## 1.0.1 / 2019-02-18

* [Fixed] Refactor openstack_controller check cache. See [#3120](https://github.com/DataDog/integrations-core/pull/3120).

## 1.0.0 / 2019-02-04

* [Added] OpenStack Controller. See [#2496](https://github.com/DataDog/integrations-core/pull/2496).


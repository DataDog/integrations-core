# CHANGELOG - HPE Aruba EdgeConnect

<!-- towncrier release notes start -->

## 1.2.0-beta.1 / 2026-11-10

***Added***:

* Add an `orchestrator_api_key` option to authenticate to the Orchestrator with an API key. ([#25536](https://github.com/DataDog/integrations-core/pull/25536))
* Add failover support with Agent High Availability feature. ([#25896](https://github.com/DataDog/integrations-core/pull/25896))

***Fixed***:

* Report `orchestrator.reachability` as 0 when the Orchestrator fails to return the appliance list. ([#25536](https://github.com/DataDog/integrations-core/pull/25536))
* Avoid resending outstanding alarms as events when the alarm cache is empty, such as on a first run or after an HA failover. ([#25896](https://github.com/DataDog/integrations-core/pull/25896))

## 1.1.0 / 2026-10-01 / Agent 7.85.0

***Added***:

* Add an `orchestrator_login_type` option so the Orchestrator can authenticate accounts defined on a RADIUS or TACACS+ server. ([#25296](https://github.com/DataDog/integrations-core/pull/25296))

## 1.0.1 / 2026-07-08 / Agent 7.82.0

***Fixed***:

* Validate appliance IP addresses from Orchestrator response before connecting to appliances. ([#24130](https://github.com/DataDog/integrations-core/pull/24130))

## 1.0.0 / 2026-06-09 / Agent 7.81.0

***Added***:

* Initial Release ([#23594](https://github.com/DataDog/integrations-core/pull/23594))

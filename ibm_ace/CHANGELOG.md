# CHANGELOG - IBM ACE

## Unreleased

## 1.2.1 / 2023-07-13

***Fixed***:

* Bump the minimum datadog-checks-base version. See [#15217](https://github.com/DataDog/integrations-core/pull/15217).

## 1.2.0 / 2023-07-10

***Added***:

* Bump dependencies for Agent 7.47. See [#15145](https://github.com/DataDog/integrations-core/pull/15145).

***Fixed***:

* Bump Python version from py3.8 to py3.9. See [#14701](https://github.com/DataDog/integrations-core/pull/14701).

## 1.1.0 / 2023-06-05

***Fixed***:

* Use `non_durable` queues when connecting to IBM Ace and also delete the subscription when disconnecting. See [#14568](https://github.com/DataDog/integrations-core/pull/14568).

## 1.0.4 / 2023-02-15 / Agent 7.44.0

***Fixed***:

* Use `count` instead of `monotonic_count` for counters. See [#13959](https://github.com/DataDog/integrations-core/pull/13959).

## 1.0.3 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates. See [#12653](https://github.com/DataDog/integrations-core/pull/12653).
* Submit error message with non-OK service check statuses. See [#12523](https://github.com/DataDog/integrations-core/pull/12523).

## 1.0.2 / 2022-05-15 / Agent 7.37.0

***Fixed***:

* Fix enumerated integer validation. See [#11964](https://github.com/DataDog/integrations-core/pull/11964).

## 1.0.1 / 2022-04-14 / Agent 7.36.0

***Fixed***:

* Enable py3 only. See [#11833](https://github.com/DataDog/integrations-core/pull/11833).

## 1.0.0 / 2022-04-04

***Added***:

* Add IBM ACE integration. See [#11654](https://github.com/DataDog/integrations-core/pull/11654).

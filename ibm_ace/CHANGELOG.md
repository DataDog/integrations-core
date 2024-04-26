# CHANGELOG - IBM ACE

<!-- towncrier release notes start -->

## 2.2.2 / 2024-04-26

***Fixed***:

* Do not fail if no tags are provided in the config ([#17336](https://github.com/DataDog/integrations-core/pull/17336))

## 2.2.1 / 2024-01-10 / Agent 7.51.0

***Fixed***:

* Properly drop support for Python 2 ([#16589](https://github.com/DataDog/integrations-core/pull/16589))

## 2.2.0 / 2024-01-05

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 2.1.0 / 2023-08-18 / Agent 7.48.0

***Added***:

* Add hostname as part of the subscription substring ([#15189](https://github.com/DataDog/integrations-core/pull/15189))

## 2.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 1.2.1 / 2023-07-13 / Agent 7.47.0

***Fixed***:

* Bump the minimum datadog-checks-base version ([#15217](https://github.com/DataDog/integrations-core/pull/15217))

## 1.2.0 / 2023-07-10

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 1.1.0 / 2023-06-05

***Fixed***:

* Use `non_durable` queues when connecting to IBM Ace and also delete the subscription when disconnecting ([#14568](https://github.com/DataDog/integrations-core/pull/14568))

## 1.0.4 / 2023-02-15 / Agent 7.44.0

***Fixed***:

* Use `count` instead of `monotonic_count` for counters ([#13959](https://github.com/DataDog/integrations-core/pull/13959))

## 1.0.3 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))
* Submit error message with non-OK service check statuses ([#12523](https://github.com/DataDog/integrations-core/pull/12523))

## 1.0.2 / 2022-05-15 / Agent 7.37.0

***Fixed***:

* Fix enumerated integer validation ([#11964](https://github.com/DataDog/integrations-core/pull/11964))

## 1.0.1 / 2022-04-14 / Agent 7.36.0

***Fixed***:

* Enable py3 only ([#11833](https://github.com/DataDog/integrations-core/pull/11833))

## 1.0.0 / 2022-04-04

***Added***:

* Add IBM ACE integration ([#11654](https://github.com/DataDog/integrations-core/pull/11654))

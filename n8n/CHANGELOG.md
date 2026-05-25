# CHANGELOG - n8n

<!-- towncrier release notes start -->

## 2.0.0 / 2026-05-20

***Changed***:

* Improve the n8n metric coverage:

    - Correct missing or incorrect metrics.
    - Add metrics introduced in n8n 2.x (workflow execution duration, audit events, authentication, workflow and user statistics, expression engine, and process memory).
    - Track n8n's dynamic events (workflow cancellations, audit activity, AI nodes, user and credential changes, package and variable changes).
    - Add support for monitoring n8n worker processes alongside the main process. ([#23635](https://github.com/DataDog/integrations-core/pull/23635))

## 1.1.2 / 2026-05-14

***Fixed***:

* Fix default raw metric prefix. ([#23598](https://github.com/DataDog/integrations-core/pull/23598))

## 1.1.1 / 2026-04-15 / Agent 7.79.0

***Fixed***:

* Improve descriptions ([#23047](https://github.com/DataDog/integrations-core/pull/23047))

## 1.1.0 / 2026-04-01 / Agent 7.78.1

***Added***:

* Add support for security validation in models ([#23109](https://github.com/DataDog/integrations-core/pull/23109))

## 1.0.0 / 2026-03-18

***Added***:

* Initial Release ([#21835](https://github.com/DataDog/integrations-core/pull/21835))

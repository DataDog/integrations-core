# CHANGELOG - Prefect

<!-- towncrier release notes start -->

## 2.2.0 / 2026-11-25

***Added***:

* Support combined basic authentication credentials in the Prefect check. ([#25596](https://github.com/DataDog/integrations-core/pull/25596))

***Fixed***:

* Add the missing license headers. ([#25983](https://github.com/DataDog/integrations-core/pull/25983))
* Fix the work queue backlog size and age metrics dropping flow runs that stay overdue for more than one collection interval. ([#26025](https://github.com/DataDog/integrations-core/pull/26025))

## 2.1.0 / 2026-10-29 / Agent 7.86.0

***Added***:

* Improve Prefect monitoring:
  - Add concurrency limit metrics for global and task run concurrency limits.
  - Add a `concurrency_limit_type` tag (`global` or `tag`) to concurrency limit metrics, and a `concurrency_limit.is_active` metric for global limits.
  - Add a `flow_name` tag to deployment, flow run and task run metrics.
  - Add `prefect_tag` tags: one per deployment tag on deployment and flow run metrics, and one per task run tag on task run metrics.
  - Add a `flow_names` option to filter by flow. ([#25529](https://github.com/DataDog/integrations-core/pull/25529))

## 2.0.0 / 2026-10-01 / Agent 7.85.0

***Changed***:

* Add support for standard HTTP configuration options (TLS, authentication, proxy, timeouts, headers) and remove the `custom_headers` option in favor of the standard `headers`/`extra_headers` options. ([#25259](https://github.com/DataDog/integrations-core/pull/25259))

## 1.2.0 / 2026-09-02 / Agent 7.84.0

***Added***:

* Add ``metrics_prefix`` to the ``discovery`` block of ``auto_conf.yaml``. ([#24861](https://github.com/DataDog/integrations-core/pull/24861))

## 1.1.0 / 2026-08-05 / Agent 7.83.0

***Added***:

* Add container-based config discovery support. ([#24483](https://github.com/DataDog/integrations-core/pull/24483))

***Fixed***:

* Require `datadog-checks-base>=37.41.0` since config discovery relies on it. ([#24545](https://github.com/DataDog/integrations-core/pull/24545))

## 1.0.1 / 2026-04-21 / Agent 7.79.0

***Fixed***:

* Adds validation for event pagination URLs. ([#23354](https://github.com/DataDog/integrations-core/pull/23354))

## 1.0.0 / 2026-03-18 / Agent 7.78.1

***Added***:

* Initial Release ([#22757](https://github.com/DataDog/integrations-core/pull/22757))

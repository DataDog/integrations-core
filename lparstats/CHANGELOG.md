# CHANGELOG - lparstats

<!-- towncrier release notes start -->

## 1.0.1 / 2026-10-29

***Fixed***:

* Treat '-' in lparstat output as a statistic that does not apply to the LPAR and skip the field silently, instead of logging an INFO line every collection interval while skipping the metric. ([#25759](https://github.com/DataDog/integrations-core/pull/25759))
* Log the 'not running as root or sudo' notice once per check instance instead of on every collection interval when the agent runs as a non-root user. ([#25761](https://github.com/DataDog/integrations-core/pull/25761))

## 1.0.0 / 2026-05-13

* Initial Release ([#23451](https://github.com/DataDog/integrations-core/pull/23451))

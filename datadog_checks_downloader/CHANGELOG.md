# CHANGELOG - Datadog Checks Downloader

<!-- towncrier release notes start -->

## 4.6.0 / 2024-04-26

***Added***:

* Update dependencies ([#17319](https://github.com/DataDog/integrations-core/pull/17319))

## 4.5.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

## 4.4.0 / 2023-11-10 / Agent 7.50.0

***Added***:

* Updated dependencies. ([#16154](https://github.com/DataDog/integrations-core/pull/16154))

## 4.3.1 / 2023-09-29 / Agent 7.49.0

***Fixed***:

* Override the default test options for some integrations ([#15779](https://github.com/DataDog/integrations-core/pull/15779))

## 4.3.0 / 2023-08-25 / Agent 7.48.0

***Security***:

* Update security dependencies ([#15667](https://github.com/DataDog/integrations-core/pull/15667))
  * in-toto: 2.0.0
  * securesystemslib: 0.28.0

## 4.2.2 / 2023-07-10 / Agent 7.47.0

***Fixed***:

* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 4.2.1 / 2023-05-26 / Agent 7.46.0

***Fixed***:

* Update dependencies ([#14594](https://github.com/DataDog/integrations-core/pull/14594))

## 4.2.0 / 2023-05-24

***Added***:

* Add an option to bypass TUF and in-toto verification in the checks downloader ([#14168](https://github.com/DataDog/integrations-core/pull/14168))

## 4.1.0 / 2023-03-03 / Agent 7.44.0

***Added***:

* Prevent Alphas, Betas and RC versions of checks from being installed unless specified ([#13837](https://github.com/DataDog/integrations-core/pull/13837))

***Fixed***:

* Remove the use of the deprecated `pkg_resources` package ([#13842](https://github.com/DataDog/integrations-core/pull/13842))

## 4.0.0 / 2023-01-20 / Agent 7.43.0

***Removed***:

* Update TUF to 2.0.0 ([#13331](https://github.com/DataDog/integrations-core/pull/13331))

***Fixed***:

* Update dependencies ([#13726](https://github.com/DataDog/integrations-core/pull/13726))
* Fix path separator-related bug affecting Windows ([#13631](https://github.com/DataDog/integrations-core/pull/13631))

## 3.10.1 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))

## 3.10.0 / 2022-10-28 / Agent 7.41.0

***Added***:

* Update downloader to use v5 root layout ([#13174](https://github.com/DataDog/integrations-core/pull/13174))

***Fixed***:

* Fix setup.py keywords in datadog-checks-downloader ([#12951](https://github.com/DataDog/integrations-core/pull/12951)) Thanks [fridex](https://github.com/fridex).

## 3.9.0 / 2022-09-16 / Agent 7.40.0

***Added***:

* Add `packaging` to dependencies ([#12753](https://github.com/DataDog/integrations-core/pull/12753))

***Fixed***:

* Use packaging instead of pkg_resources for parsing version ([#12560](https://github.com/DataDog/integrations-core/pull/12560)) Thanks [fridex](https://github.com/fridex).

## 3.8.0 / 2022-08-05 / Agent 7.39.0

***Added***:

* Use context manager when creating temporary directory ([#12559](https://github.com/DataDog/integrations-core/pull/12559)) Thanks [fridex](https://github.com/fridex).

***Fixed***:

* Prevent from publishing datadog-checks-downloader to PyPI ([#12556](https://github.com/DataDog/integrations-core/pull/12556))
* Revert #12559 to make it compatible with python2 ([#12647](https://github.com/DataDog/integrations-core/pull/12647))
* Avoid using assert statement by creating UpdatedTargetsError exception ([#12558](https://github.com/DataDog/integrations-core/pull/12558))
* Adjust logging setup when multiple -v flags are supplied ([#12562](https://github.com/DataDog/integrations-core/pull/12562)) Thanks [fridex](https://github.com/fridex).

## 3.7.0 / 2022-04-11 / Agent 7.36.0

***Added***:

* Update downloader to use v4 root layout ([#11779](https://github.com/DataDog/integrations-core/pull/11779))

## 3.6.0 / 2022-02-24 / Agent 7.35.0

***Added***:

* Add --ignore-python-version flag ([#11568](https://github.com/DataDog/integrations-core/pull/11568))

## 3.5.0 / 2022-02-19

***Added***:

* Add `pyproject.toml` file ([#11305](https://github.com/DataDog/integrations-core/pull/11305))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 3.4.1 / 2021-10-19 / Agent 7.32.0

***Fixed***:

* Update tuf to 0.19.0 for python 3 ([#10444](https://github.com/DataDog/integrations-core/pull/10444))

## 3.4.0 / 2021-07-09 / Agent 7.30.0

***Added***:

* Upgrade downloader after ceremony ([#9556](https://github.com/DataDog/integrations-core/pull/9556))

## 3.3.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Better error message if the integration doesn't have the expected type ([#9403](https://github.com/DataDog/integrations-core/pull/9403))

## 3.2.0 / 2020-10-31 / Agent 7.24.0

***Security***:

* Update TUF, in-toto and securesystemslib ([#7844](https://github.com/DataDog/integrations-core/pull/7844))

## 3.1.1 / 2020-09-21 / Agent 7.23.0

***Fixed***:

* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 3.1.0 / 2020-07-14 / Agent 7.21.1

***Added***:

* Update to v6 root from @FlorianVeaux ([#7115](https://github.com/DataDog/integrations-core/pull/7115))
* Add warning when selecting an extras integration that resides in core ([#7079](https://github.com/DataDog/integrations-core/pull/7079))
* Add dependencies to setup.py ([#7030](https://github.com/DataDog/integrations-core/pull/7030))

## 3.0.0 / 2020-06-18 / Agent 7.21.0

***Added***:

* Support multiple root layouts ([#6856](https://github.com/DataDog/integrations-core/pull/6856))

## 2.5.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 2.4.0 / 2020-02-26 / Agent 7.18.0

***Added***:

* Bump securesystemslib to 0.14.2 ([#5890](https://github.com/DataDog/integrations-core/pull/5890))

## 2.3.1 / 2020-02-24

***Fixed***:

* Hide internal logging exceptions ([#5848](https://github.com/DataDog/integrations-core/pull/5848))

## 2.3.0 / 2020-02-22

***Added***:

* Update in-toto and its deps ([#5599](https://github.com/DataDog/integrations-core/pull/5599))

## 2.2.0 / 2020-01-10 / Agent 7.17.0

***Added***:

* Update TUF dependency ([#5441](https://github.com/DataDog/integrations-core/pull/5441))
* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))

## 2.1.0 / 2020-01-02

***Changed***:

* Don't provide a CLI entry point ([#5374](https://github.com/DataDog/integrations-core/pull/5374))

## 2.0.0 / 2019-12-05 / Agent 7.16.0

***Fixed***:

* Clean up test artifacts ([#5129](https://github.com/DataDog/integrations-core/pull/5129))

## 0.7.0 / 2019-12-02

***Added***:

* Support downloading universal and pure Python wheels ([#4981](https://github.com/DataDog/integrations-core/pull/4981))

## 0.6.0 / 2019-06-01 / Agent 6.12.0

***Added***:

* Update downloader to new TUF root v4 ([#3811](https://github.com/DataDog/integrations-core/pull/3811))

## 0.5.0 / 2019-05-14

***Added***:

* Allow users to override TUF repository URL prefix ([#3660](https://github.com/DataDog/integrations-core/pull/3660))
* Adhere to code style ([#3498](https://github.com/DataDog/integrations-core/pull/3498))

## 0.4.0 / 2019-03-29 / Agent 6.11.0

***Added***:

* Refactor CLI code ([#3317](https://github.com/DataDog/integrations-core/pull/3317))
* Upgrade in-toto ([#3411](https://github.com/DataDog/integrations-core/pull/3411))

***Fixed***:

* Never chdir back to a directory we don't control ([#3282](https://github.com/DataDog/integrations-core/pull/3282))
* Fix pylint ([#3190](https://github.com/DataDog/integrations-core/pull/3190))

## 0.3.0 / 2019-02-22 / Agent 6.10.0

***Added***:

* Allow `datadog_checks_downloader` to be securely updated ([#3184](https://github.com/DataDog/integrations-core/pull/3184))
* Move exceptions to their own submodule ([#3180](https://github.com/DataDog/integrations-core/pull/3180))

***Fixed***:

* Increase requests timeout ([#3182](https://github.com/DataDog/integrations-core/pull/3182))

## 0.2.0 / 2019-02-20

***Added***:

* Add __main__ module to package ([#3108](https://github.com/DataDog/integrations-core/pull/3108))

***Fixed***:

* Better error message when no such DD package or version ([#3161](https://github.com/DataDog/integrations-core/pull/3161))
* Use Cloudfront instead of direct-to-S3 ([#3087](https://github.com/DataDog/integrations-core/pull/3087))

## 0.1.0 / 2019-02-05

***Added***:

* Add datadog-checks-downloader ([#3026](https://github.com/DataDog/integrations-core/pull/3026))

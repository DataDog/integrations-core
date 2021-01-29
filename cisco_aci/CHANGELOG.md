# CHANGELOG - cisco_aci

## 1.13.0 / 2021-01-28

* [Security] Upgrade cryptography python package. See [#8476](https://github.com/DataDog/integrations-core/pull/8476).

## 1.12.0 / 2020-10-31 / Agent 7.24.0

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Security] Upgrade `cryptography` dependency. See [#7869](https://github.com/DataDog/integrations-core/pull/7869).

## 1.11.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).
* [Fixed] Update proxy section in conf.yaml. See [#7336](https://github.com/DataDog/integrations-core/pull/7336).

## 1.10.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] DOCS-838 Template wording. See [#7038](https://github.com/DataDog/integrations-core/pull/7038).

## 1.10.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add note about warning concurrency. See [#6967](https://github.com/DataDog/integrations-core/pull/6967).

## 1.9.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Add config spec. See [#6314](https://github.com/DataDog/integrations-core/pull/6314).

## 1.8.4 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.8.3 / 2020-02-22 / Agent 7.18.0

* [Fixed] Update request wrapper with password and A6 signature. See [#5684](https://github.com/DataDog/integrations-core/pull/5684).

## 1.8.2 / 2019-12-27 / Agent 7.17.0

* [Fixed] Ensure only one session object per url. See [#5334](https://github.com/DataDog/integrations-core/pull/5334).

## 1.8.1 / 2019-12-02 / Agent 7.16.0

* [Fixed] Use RequestsWrapper. See [#5037](https://github.com/DataDog/integrations-core/pull/5037).

## 1.8.0 / 2019-11-20

* [Added] Upgrade cryptography to 2.8. See [#5047](https://github.com/DataDog/integrations-core/pull/5047).
* [Fixed] Refresh auth token when it expires. See [#5039](https://github.com/DataDog/integrations-core/pull/5039).
* [Added] Standardize logging format. See [#4902](https://github.com/DataDog/integrations-core/pull/4902).

## 1.7.2 / 2019-08-24 / Agent 6.14.0

* [Fixed] Use utcnow instead of now. See [#4192](https://github.com/DataDog/integrations-core/pull/4192).

## 1.7.1 / 2019-07-08 / Agent 6.13.0

* [Fixed] Fix event submission call. See [#4044](https://github.com/DataDog/integrations-core/pull/4044).

## 1.7.0 / 2019-07-04

* [Added] Update cryptography version. See [#4000](https://github.com/DataDog/integrations-core/pull/4000).

## 1.6.0 / 2019-06-01 / Agent 6.12.0

* [Added] Improve API logs. See [#3794](https://github.com/DataDog/integrations-core/pull/3794).
* [Fixed] Sanitize external host tags. See [#3792](https://github.com/DataDog/integrations-core/pull/3792).

## 1.5.0 / 2019-05-14

* [Added] Adhere to code style. See [#3489](https://github.com/DataDog/integrations-core/pull/3489).

## 1.4.0 / 2019-02-18 / Agent 6.10.0

* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).
* [Added] Support Python 3. See [#3029](https://github.com/DataDog/integrations-core/pull/3029).

## 1.3.0 / 2018-11-30 / Agent 6.8.0

* [Added] Upgrade cryptography. See [#2659][1].
* [Fixed] Use raw string literals when \ is present. See [#2465][2].

## 1.2.1 / 2018-10-12 / Agent 6.6.0

* [Fixed] fixes cisco for username and password. See [#2267][3].

## 1.2.0 / 2018-09-04 / Agent 6.5.0

* [Added] Use Certs in the Cisco Check as well as Passwords. See [#1986][4].
* [Fixed] Add data files to the wheel package. See [#1727][5].

## 1.1.0 / 2018-06-21 / Agent 6.4.0

* [Fixed] Makes the Cisco Check more resilient. See [#1785][6].

## 1.0.0 / 2018-06-07

* [FEATURE] adds CiscoACI integration.
[1]: https://github.com/DataDog/integrations-core/pull/2659
[2]: https://github.com/DataDog/integrations-core/pull/2465
[3]: https://github.com/DataDog/integrations-core/pull/2267
[4]: https://github.com/DataDog/integrations-core/pull/1986
[5]: https://github.com/DataDog/integrations-core/pull/1727
[6]: https://github.com/DataDog/integrations-core/pull/1785

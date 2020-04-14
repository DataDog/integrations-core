# CHANGELOG - cisco_aci

## 1.8.4 / 2020-04-04

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.8.3 / 2020-02-22

* [Fixed] Update request wrapper with password and A6 signature. See [#5684](https://github.com/DataDog/integrations-core/pull/5684).

## 1.8.2 / 2019-12-27

* [Fixed] Ensure only one session object per url. See [#5334](https://github.com/DataDog/integrations-core/pull/5334).

## 1.8.1 / 2019-12-02

* [Fixed] Use RequestsWrapper. See [#5037](https://github.com/DataDog/integrations-core/pull/5037).

## 1.8.0 / 2019-11-20

* [Added] Upgrade cryptography to 2.8. See [#5047](https://github.com/DataDog/integrations-core/pull/5047).
* [Fixed] Refresh auth token when it expires. See [#5039](https://github.com/DataDog/integrations-core/pull/5039).
* [Added] Standardize logging format. See [#4902](https://github.com/DataDog/integrations-core/pull/4902).

## 1.7.2 / 2019-08-24

* [Fixed] Use utcnow instead of now. See [#4192](https://github.com/DataDog/integrations-core/pull/4192).

## 1.7.1 / 2019-07-08

* [Fixed] Fix event submission call. See [#4044](https://github.com/DataDog/integrations-core/pull/4044).

## 1.7.0 / 2019-07-04

* [Added] Update cryptography version. See [#4000](https://github.com/DataDog/integrations-core/pull/4000).

## 1.6.0 / 2019-06-01

* [Added] Improve API logs. See [#3794](https://github.com/DataDog/integrations-core/pull/3794).
* [Fixed] Sanitize external host tags. See [#3792](https://github.com/DataDog/integrations-core/pull/3792).

## 1.5.0 / 2019-05-14

* [Added] Adhere to code style. See [#3489](https://github.com/DataDog/integrations-core/pull/3489).

## 1.4.0 / 2019-02-18

* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).
* [Added] Support Python 3. See [#3029](https://github.com/DataDog/integrations-core/pull/3029).

## 1.3.0 / 2018-11-30

* [Added] Upgrade cryptography. See [#2659][1].
* [Fixed] Use raw string literals when \ is present. See [#2465][2].

## 1.2.1 / 2018-10-12

* [Fixed] fixes cisco for username and password. See [#2267][3].

## 1.2.0 / 2018-09-04

* [Added] Use Certs in the Cisco Check as well as Passwords. See [#1986][4].
* [Fixed] Add data files to the wheel package. See [#1727][5].

## 1.1.0 / 2018-06-21

* [Fixed] Makes the Cisco Check more resilient. See [#1785][6].

## 1.0.0 / 2018-06-07

* [FEATURE] adds CiscoACI integration.
[1]: https://github.com/DataDog/integrations-core/pull/2659
[2]: https://github.com/DataDog/integrations-core/pull/2465
[3]: https://github.com/DataDog/integrations-core/pull/2267
[4]: https://github.com/DataDog/integrations-core/pull/1986
[5]: https://github.com/DataDog/integrations-core/pull/1727
[6]: https://github.com/DataDog/integrations-core/pull/1785

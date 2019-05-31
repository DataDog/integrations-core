# Datadog Agent Integrations - Core

[![Build status][1]][2]
[![Build status][3]][4]
[![Coverage status][17]][18]
[![Documentation Status][19]][20]
[![Code style - black][21]][22]

This repository contains the Agent Integrations (also known as checks) that Datadog
officially develops and supports. To add a new integration, please see the [Integrations Extras][5]
repository and the [accompanying documentation][6].

The [Datadog Agent][7] packages are equipped with all the Integrations from this
repository, so to get started using them, you can simply [install the Agent][8]
for your operating system. The [AGENT_CHANGELOG](AGENT_CHANGELOG.md) file shows
which Integrations have been updated in each Agent version.

## Integrations as Python wheels

When working with an integration, you will now be dealing with a more structured
python project. The new structure should help keep a more sane and modular codebase.
To help with the transition, please take a look at the following map to understand
where everything falls into place in the new approach.

| FORMER LOCATION               | NEW LOCATION                                      |
| ---------------               | ------------                                      |
| `{integration}/check.py`      | `{integration}/datadog_checks/{integration}/*.py` |
| `{integration}/test_check.py` | `{integration}/tests/*.py`                        |
| n/a                           | `{integration}/setup.py`                          |

Now that integrations are cleanly defined as python packages, we will soon be able
to ship them as Python wheels that will be pip-installable in the Python environment
embedded into the Datadog Agent. This presents a paradigm change in the way we will
be delivering standalone integration upgrades, moving away from OS-specific packages
to idiomatic Python package delivery.

## Contributing

Working with integrations is easy, the main page of the [development docs][6]
contains all the info you need to get your dev environment up and running in minutes
to run, test and build a Check. More advanced API documentation can be found [here][20]

## Reporting Issues

For more information on integrations, please reference our [documentation][11]
and [knowledge base][12]. You can also visit our
[help page][13] to connect with us.

## GPG public keys

For those whom it may concern, the following is a list of GPG public key
fingerprints known to correspond to developers who, at the time of writing (May
28 2019), can trigger a build by signing [metadata](.links/):

* [Christine Chen](https://api.github.com/users/ChristineTChen/gpg_keys)
  * `57CE 2495 EA48 D456 B9C4  BA4F 66E8 2239 9141 D9D3`
  * `36C0 82E7 38C7 B4A1 E169  11C0 D633 59C4 875A 1A9A`
* [Dave Coleman](https://api.github.com/users/dcoleman17/gpg_keys)
  * `8278 C406 C1BB F1F2 DFBB  5AD6 0AE7 E246 4F8F D375`
  * `98A5 37CD CCA2 8DFF B35B  0551 5D50 0742 90F6 422F`
* [Hippolyte Henry](https://api.github.com/users/zippolyte/gpg_keys)
  * `87D5 2666 ECBF 2459 9D5A  594F F7AC E411 B85D 518C`
  * `31EE F81D 7F71 6E35 83F2  4095 55D1 30B4 49D2 BD26`
* [Thomas Hervé](https://api.github.com/users/therve/gpg_keys)
  * `59DB 2532 75A5 BD4E 55C7  C5AA 0678 55A2 8E90 3B3B`
  * `E2BD 994F 95C0 BC0B B923  1D21 F752 1EC8 F485 90D0`
* [Slavek Kabrda](https://api.github.com/users/bkabrda/gpg_keys)
  * `9DC4 CA38 900B 533E 3BC0  22A7 001F 609E 8B8F 2ED7`
  * `CDBE 0233 B8A1 095E D6CD  A197 F8DA AD10 7BBE 268B`
* [Ofek Lev](https://api.github.com/users/ofek/gpg_keys)
  * `C295 CF63 B355 DFEB 3316  02F7 F426 A944 35BE 6F99`
  * `D009 8861 8057 D2F4 D855  5A62 B472 442C B7D3 AF42`
* [Nicholas Muesch](https://api.github.com/users/nmuesch/gpg_keys)
  * `6E09 1A53 0468 B148 54BB  6CCE 831C 23C4 9BBE 61F8`
  * `BACE F480 6D0B 4FBE D227  DC3B C0E2 8E5E 241E D25A`
* [Massimiliano Pippi](https://api.github.com/users/masci/gpg_keys)
  * `BE9C 5131 8EED C03F E901  F256 C2C8 965F 07D0 A23D`
  * `69CA DE35 4030 5312 54AF  170C 50A7 66D9 4DFC 27CC`
* [Julia Simon](https://api.github.com/users/hithwen/gpg_keys)
  * `4A54 09A2 3361 109C 047C  C76A DC8A 42C2 8B95 0123`
  * `129A 26CF A726 3C85 98A6  94B0 8659 1366 CBA1 BF3C`
* [Florian Veaux](https://api.github.com/users/FlorianVeaux/gpg_keys)
  * `3109 1C85 5D78 7789 93E5  0348 9BFE 5299 D02F 83E9`
  * `7A73 0C5E 48B0 6986 1045  CF8B 8B2D 16D6 5DE4 C95E`
* [Alexandre Yang](https://api.github.com/users/AlexandreYang/gpg_keys)
  * `FBC6 3AE0 9D0C A9B4 584C  9D7F 4291 A11A 36EA 52CD`
  * `F8D9 181D 9309 F8A4 957D  636A 27F8 F48B 18AE 91AA`
* [Greg Zussa](https://api.github.com/users/gzussa/gpg_keys)
  * `D24D 57CE 96BD F8C2 9BB0  BEAB C783 0ECB 08F8 8C74`
  * `3936 7937 7466 5878 C67A  50E9 3C67 09D5 583F B57C`

[1]: https://api.travis-ci.com/DataDog/integrations-core.svg?branch=master
[2]: https://travis-ci.com/DataDog/integrations-core
[3]: https://ci.appveyor.com/api/projects/status/8w4s2bilp48n43gw?svg=true
[4]: https://ci.appveyor.com/project/Datadog/integrations-core
[5]: https://github.com/DataDog/integrations-extras
[6]: https://docs.datadoghq.com/developers/integrations
[7]: https://github.com/DataDog/datadog-agent
[8]: https://docs.datadoghq.com/agent/
[9]: https://docs.pytest.org/en/latest/
[10]: https://packaging.python.org/tutorials/distributing-packages/
[11]: https://docs.datadoghq.com
[12]: https://help.datadoghq.com/hc/en-us
[13]: https://docs.datadoghq.com/help/
[15]: https://github.com/DataDog/integrations-core/blob/6.2.1/requirements-integration-core.txt
[16]: https://github.com/DataDog/integrations-core/blob/ea2dfbf1e8859333af4c8db50553eb72a3b466f9/requirements-agent-release.txt
[17]: https://codecov.io/github/DataDog/integrations-core/coverage.svg?branch=master
[18]: https://codecov.io/github/DataDog/integrations-core?branch=master
[19]: https://readthedocs.org/projects/datadog-checks-base/badge/?version=latest
[20]: https://datadog-checks-base.readthedocs.io/en/latest/?badge=latest
[21]: https://img.shields.io/badge/code%20style-black-000000.svg
[22]: https://github.com/ambv/black

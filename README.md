# Datadog Agent Integrations - Core

[![Build status][1]][2]
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
fingerprints known to correspond to developers who, at the time of writing (Dec
2 2019), can trigger a build by signing [metadata](.in-toto/):

* [Christine Chen](https://api.github.com/users/ChristineTChen/gpg_keys)
  * `57CE 2495 EA48 D456 B9C4  BA4F 66E8 2239 9141 D9D3`
  * `36C0 82E7 38C7 B4A1 E169  11C0 D633 59C4 875A 1A9A`
* [Dave Coleman](https://api.github.com/users/dcoleman17/gpg_keys)
  * `8278 C406 C1BB F1F2 DFBB  5AD6 0AE7 E246 4F8F D375`
  * `98A5 37CD CCA2 8DFF B35B  0551 5D50 0742 90F6 422F`
* [Mike Garabedian](https://api.github.com/users/mgarabed/gpg_keys)
  * `F90C 0097 67F2 4B27 9DC2  C83D A227 6601 6CB4 CF1D`
  * `2669 6E67 28D2 0CB0 C1E0  D2BE 6643 5756 8398 9306`
* [Thomas Hervé](https://api.github.com/users/therve/gpg_keys)
  * `59DB 2532 75A5 BD4E 55C7  C5AA 0678 55A2 8E90 3B3B`
  * `E2BD 994F 95C0 BC0B B923  1D21 F752 1EC8 F485 90D0`
* [Ofek Lev](https://api.github.com/users/ofek/gpg_keys)
  * `C295 CF63 B355 DFEB 3316  02F7 F426 A944 35BE 6F99`
  * `D009 8861 8057 D2F4 D855  5A62 B472 442C B7D3 AF42`
* [Florimond Manca](https://api.github.com/users/florimondmanca/gpg_keys)
  * `B023 B02A 0331 9CD8 D19A  4328 83ED 89A4 5548 48FC`
  * `0992 11D9 AA67 D21E 7098  7B59 7C7D CB06 C9F2 0C13`
* [Julia Simon](https://api.github.com/users/hithwen/gpg_keys)
  * `4A54 09A2 3361 109C 047C  C76A DC8A 42C2 8B95 0123`
  * `129A 26CF A726 3C85 98A6  94B0 8659 1366 CBA1 BF3C`
* [Florian Veaux](https://api.github.com/users/FlorianVeaux/gpg_keys)
  * `3109 1C85 5D78 7789 93E5  0348 9BFE 5299 D02F 83E9`
  * `7A73 0C5E 48B0 6986 1045  CF8B 8B2D 16D6 5DE4 C95E`
* [Alexandre Yang](https://api.github.com/users/AlexandreYang/gpg_keys)
  * `FBC6 3AE0 9D0C A9B4 584C  9D7F 4291 A11A 36EA 52CD`
  * `F8D9 181D 9309 F8A4 957D  636A 27F8 F48B 18AE 91AA`

[1]: https://dev.azure.com/datadoghq/integrations-core/_apis/build/status/Master%20All?branchName=master
[2]: https://dev.azure.com/datadoghq/integrations-core/_build/latest?definitionId=29&branchName=master
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

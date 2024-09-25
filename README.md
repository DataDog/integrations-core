# Datadog Integrations - Core

| | |
| --- | --- |
| CI/CD | [![CI - Test][1]][2] [![CI - Coverage][17]][18] |
| Docs | [![Docs - Release][19]][20] |
| Meta | [![Hatch project][26]][27] [![Linting - Ruff][24]][25] [![Code style - black][21]][22] [![Typing - Mypy][28]][29] [![License - BSD-3-Clause][30]][31] |

This repository contains open source integrations that Datadog officially develops and supports.
To add a new integration, please see the [Integrations Extras][5] repository and the
[accompanying documentation][6].

The [Datadog Agent][7] packages are equipped with all the Agent integrations from this
repository, so to get started using them, you can simply [install the Agent][8]
for your operating system. The [AGENT_CHANGELOG](AGENT_CHANGELOG.md) file shows
which Integrations have been updated in each Agent version.

## Contributing

Working with integrations is easy, the main page of the [development docs][6]
contains all the info you need to get your dev environment up and running in minutes
to run, test and build a Check. More advanced documentation can be found [here][3].

## Reporting Issues

For more information on integrations, please reference our [documentation][11] and
[knowledge base][12]. You can also visit our [help page][13] to connect with us.


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/badges/test-results.svg
[2]: https://github.com/DataDog/integrations-core/actions/workflows/master.yml
[3]: https://datadoghq.dev/integrations-core/
[5]: https://github.com/DataDog/integrations-extras
[6]: https://docs.datadoghq.com/developers/integrations/
[7]: https://github.com/DataDog/datadog-agent
[8]: https://app.datadoghq.com/account/settings/agent/latest
[9]: https://docs.pytest.org/en/latest/
[10]: https://packaging.python.org/tutorials/distributing-packages/
[11]: https://docs.datadoghq.com
[12]: https://help.datadoghq.com/hc/en-us
[13]: https://docs.datadoghq.com/help/
[15]: https://github.com/DataDog/integrations-core/blob/6.2.1/requirements-integration-core.txt
[16]: https://github.com/DataDog/integrations-core/blob/ea2dfbf1e8859333af4c8db50553eb72a3b466f9/requirements-agent-release.txt
[17]: https://codecov.io/github/DataDog/integrations-core/coverage.svg?branch=master
[18]: https://codecov.io/github/DataDog/integrations-core?branch=master
[19]: https://github.com/DataDog/integrations-core/workflows/docs/badge.svg
[20]: https://github.com/DataDog/integrations-core/actions?workflow=docs
[21]: https://img.shields.io/badge/code%20style-black-000000.svg
[22]: https://github.com/ambv/black
[24]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json
[25]: https://github.com/charliermarsh/ruff
[26]: https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg
[27]: https://github.com/pypa/hatch
[28]: https://img.shields.io/badge/typing-Mypy-blue.svg
[29]: https://github.com/python/mypy
[30]: https://img.shields.io/badge/license-BSD--3--Clause-9400d3.svg
[31]: https://spdx.org/licenses/BSD-3-Clause.html

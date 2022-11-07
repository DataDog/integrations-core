---
title: Create an Agent integration
kind: documentation
further_reading:
- link: "logs/processing/pipelines"
  tag: "Documentation"
  text: "Log processing pipelines"
aliases:
  - /developers/integrations/integration_sdk/
  - /developers/integrations/testing/
  - /integrations/datadog_checks_dev/
  - /guides/new_integration/
  - /developers/integrations/new_check_howto/
---

This guide provides instructions for creating a Datadog Agent integration in the integrations-extras repo. For information on why you'd want to create an Agent integration, see [Creating your own solution][1].

## Prerequisites

The datadog Agent development tools require:
- Python 3.8+.
- [Docker][2] (to run the full test suite)

### Install Python

Many operating systems come with a pre-installed version of Python. However, the version of Python installed by default might be older than the version used in the Agent, and might lack required tools and dependencies. To ensure that you have everything you need to get an integration running. Install a dedicated Python interpreter.

Some options for installing Python on your operating system:
- Follow the [official Python documentation][3] to download and install the Python interpreter.
- Use a Python version manager like [pyenv][4].

On most operating systems, Python versions after 3.3 come with a pre-installed version manager called `venv`, which is used in this guide. Debian/Ubuntu installations do not come packaged with `venv`. You can install it by running `sudo apt-get install python3-venv`.

## Set up your development environment

1. Create the `dd` directory and clone the [`integrations-extras` repo][5].

   **Note**: The Datadog development toolkit expects you to work in the `$HOME/dd/` directory. This is not mandatory, but working in a different directory necessitates more configuration steps.

   To create the `dd` directory and clone the `datadog-extras` repo:
   ```shell
   mkdir $HOME/dd && cd $HOME/dd
   git clone https://github.com/DataDog/integrations-extras.git
   ```

1. (Optional) It's good practice to set up a [Python virtual environment][6] to isolate your development environment:

   ```shell
   cd $HOME/dd/integrations-extras
   python3 -m venv venv
   . venv/bin/activate
   ```

   **Tip**: If you ever want to exit the virtual environment, run `deactivate`.

1. Make sure the python `wheel` package is installed and up-to-date:
   ```shell
   pip3 install wheel
   ```

1. Install the [Developer Toolkit][7]:
   ```bash
   pip3 install "datadog-checks-dev[cli]"
   ```

1. (Optional) If you cloned the `integrations-extras` to somewhere other than `$HOME/dd/`, adjust the configuration file:

   ```shell
   ddev config set extras "/path/to/integrations-extras"
   ```

1. Set `integrations-extras` as the default working repo:

   ```shell
   ddev config set repo extras
   ```

You're ready to create your integration!

## Create your integration

The instructions below use an example integration called Awesome. Follow along using the code from Awesome, or replace Awesome with your own integration code.

### Scaffolding

The `ddev create` command runs an interactive tool that helps you to create the basic file and path structure (or "scaffolding") necessary for a new integration.

1. Before you create your first integration directory, try a dry-run using the `-n/--dry-run` flag, which doesn't write anything to disk:

   ```bash
   ddev create -n Awesome
   ```

   The command displays the path where the files would have been written, as well as the structure itself. Make sure the path in the first line of output matches your integrations-extras repository location.

1. Now run the command without the `-n` flag. The tool asks you for an email and name and then creates the files you need to get started with an integration.

   ```shell
   ddev create Awesome
   ```

## Write an Agent Check

At the core of each integration is an Agent Check that periodically collects information and sends it to Datadog. Checks inherit their logic from the `AgentCheck` base class and have the the following requirements:

- Integrations run on Agent v7+ must be Python 3 compatible; however, Agents v5 and v6 still use Python 2.7.
- Checks must derive from `AgentCheck`
- Checks must provide a method with this signature: `check(self, instance)`

Checks are organized in regular Python packages under the `datadog_checks` namespace. For example, the code for Awesome lives in the `awesome/datadog_checks/awesome/` directory.
- The name of the package must be the same as the check name.
- There are no restrictions on the name of the Python modules within that package, nor on the name of the class implementing the check.

### Implement check logic

For Awesome, the Agent Check is composed only of a Service Check named `awesome.search` that searches for a string on a web page. It results in `OK` if the string is present, `WARNING` if the page is accessible but the string was not found, and `CRITICAL` if the page is inaccessible. See the [Metric Submission: Custom Agent Check][8] if you want to learn how to submit metrics with your Agent Check.

The code contained within `awesome/datadog_checks/awesome/check.py` looks something like this:

```python
import requests

from datadog_checks.base import AgentCheck, ConfigurationError


class AwesomeCheck(AgentCheck):
    """AwesomeCheck derives from AgentCheck, and provides the required check method."""

    def check(self, instance):
        url = instance.get('url')
        search_string = instance.get('search_string')

        # It's a very good idea to do some basic sanity checking.
        # Try to be as specific as possible with the exceptions.
        if not url or not search_string:
            raise ConfigurationError('Configuration error, please fix awesome.yaml')

        try:
            response = requests.get(url)
            response.raise_for_status()
        # Something went horribly wrong
        except Exception as e:
            # Ideally we'd use a more specific message...
            self.service_check('awesome.search', self.CRITICAL, message=str(e))
        # Page is accessible
        else:
            # search_string is present
            if search_string in response.text:
                self.service_check('awesome.search', self.OK)
            # search_string was not found
            else:
                self.service_check('awesome.search', self.WARNING)
```

To learn more about the base Python class, see [Anatomy of a Python Check][9].

## Write tests

There are two basic types of tests:
- Unit tests for specific functionality.
- Integration tests that execute the `check` method and verify proper metrics collection.

Tests are required if you want your integration to be included in `integrations-extras`.

**Note**: [pytest][10] and [tox][11] are used to run the tests.

### Write a unit test

The first part of the `check` method for Awesome retrieves and verifies two elements from the configuration file. This is a good candidate for a unit test. Open the file at `awesome/tests/test_awesome.py` and replace the contents with something like this:

```python
import pytest

# Don't forget to import your integration!
from datadog_checks.awesome import AwesomeCheck
from datadog_checks.base import ConfigurationError


@pytest.mark.unit
def test_config():
    instance = {}
    c = AwesomeCheck('awesome', {}, [instance])

    # empty instance
    with pytest.raises(ConfigurationError):
        c.check(instance)

    # only the url
    with pytest.raises(ConfigurationError):
        c.check({'url': 'http://foobar'})

    # only the search string
    with pytest.raises(ConfigurationError):
        c.check({'search_string': 'foo'})

    # this should not fail
    c.check({'url': 'http://foobar', 'search_string': 'foo'})
```

`pytest` has the concept of markers that can be used to group tests into categories. Notice that `test_config` is marked as a `unit` test.

The scaffolding is set up to run all tests located in `awesome/tests`. Run the tests:

```bash
ddev test awesome
```

### Write an integration test

The unit test above doesn't check the collection logic. To test the logic, you need an integration test.

#### Create an environment for the integration test

 The toolchain uses `docker` to spin up an Nginx container and let the check retrieve the welcome page. Create a compose file at `awesome/tests/docker-compose.yml` with the following contents:

```yaml
version: "3"

services:
  nginx:
    image: nginx:stable-alpine
    ports:
      - "8000:80"
```

Next, open the file at `awesome/tests/conftest.py` and replace the contents with something like this:

```python
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here

URL = 'http://{}:8000'.format(get_docker_hostname())
SEARCH_STRING = 'Thank you for using nginx.'
INSTANCE = {'url': URL, 'search_string': SEARCH_STRING}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'docker-compose.yml')

    # This does 3 things:
    #
    # 1. Spins up the services defined in the compose file
    # 2. Waits for the url to be available before running the tests
    # 3. Tears down the services when the tests are finished
    with docker_run(compose_file, endpoints=[URL]):
        yield INSTANCE


@pytest.fixture
def instance():
    return INSTANCE.copy()
```

#### Add an integration test

Finally, add an integration test to the `awesome/tests/test_awesome.py` file:

```python
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_check(aggregator, instance):
    c = AwesomeCheck('awesome', {}, [instance])

    # the check should send OK
    c.check(instance)
    aggregator.assert_service_check('awesome.search', AwesomeCheck.OK)

    # the check should send WARNING
    instance['search_string'] = 'Apache'
    c.check(instance)
    aggregator.assert_service_check('awesome.search', AwesomeCheck.WARNING)
```

To speed up development, use the `-m/--marker` option to run only integration tests:

```bash
ddev test -m integration awesome
```

Your integration is almost done. Next, add the necessary check assets.

## Create the check assets

The set of assets created by the `ddev` scaffolding must be populated in order for a check to be considered for inclusion:

`README.md`
: This contains the documentation for your Agent Check, how to set it up, which data it collects, and so on.

`spec.yaml`
: This is used to generate `conf.yaml.example` using the `ddev` tooling (see the "Configuration template" tab below). See [Configuration specification][12] to learn more.

`conf.yaml.example`
: This contains default (or example) configuration options for your Agent Check. Do not edit this file by hand! It is generated from the contents of `spec.yaml`. See the [Configuration file reference][13] to learn its logic.

`manifest.json`
: This contains the metadata for your Agent Check such as the title and categories. See the [Manifest file reference][14] to learn more.

`metadata.csv`
: This contains the list of all metrics collected by your Agent Check. See the [Metrics metadata file reference][15] to learn more.

`service_check.json`
: This contains the list of all Service Checks collected by your Agent Check. See the [ServiceAgent Check file reference][16] to learn more.

For this example, those files would have the following form:

{{< tabs >}}
{{% tab "Configuration template" %}}

The `awesome/assets/configuration/spec.yaml` used to generate `awesome/datadog_checks/awesome/data/conf.yaml.example`:

```yaml
name: Awesome
files:
- name: awesome.yaml
  options:
  - template: init_config
    options:
    - template: init_config/default
  - template: instances
    options:
    - name: url
      required: true
      description: The URL to check.
      value:
        type: string
        example: http://example.org
    - name: search_string
      required: true
      description: The string to search for.
      value:
        type: string
        example: Example Domain
    - name: flag_follow_redirects
      # required: false is implicit; comment it to see what happens!
      required: false
      description: Follow 301 redirects.
      value:
        type: boolean
        example: false
    # Try transposing these templates to see what happens!
    #- template: instances/http
    - template: instances/default
```

Generate `conf.yaml.example` using `ddev`:

```bash
ddev validate config --sync awesome
```

{{% /tab %}}
{{% tab "Manifest" %}}

The `awesome/manifest.json` for the Awesome Service Check:

**Note**: The `guid` must be unique (and valid), so do not use the one from this example (the tooling generates one for you):

```json
{
  "display_name": "awesome",
  "maintainer": "email@example.org",
  "manifest_version": "1.0.0",
  "name": "awesome",
  "metric_prefix": "awesome.",
  "metric_to_check": "",
  "creates_events": false,
  "short_description": "",
  "guid": "x16b8750-df1e-46c0-839a-2056461b604x",
  "support": "contrib",
  "supported_os": ["linux", "mac_os", "windows"],
  "public_title": "Datadog-awesome Integration",
  "categories": ["web"],
  "type": "check",
  "is_public": false,
  "integration_id": "awesome",
  "assets": {
    "dashboards": {
      "Awesome Overview": "assets/dashboards/overview.json",
      "Awesome Investigation Dashboard": "assets/dashboards/investigation.json"
    },
    "monitors": {},
    "service_checks": "assets/service_checks.json"
  }
}
```

{{% /tab %}}
{{% tab "Metadata" %}}

The example integration doesn't send any metrics, so in this case the generated `awesome/metadata.csv` contains only the row containing CSV column names.

{{% /tab %}}
{{% tab "Service Check" %}}

The example integration contains a Service Check, so you need to add it to the `awesome/assets/service_checks.json` file:

```json
[
  {
    "agent_version": "6.0.0",
    "integration": "awesome",
    "check": "awesome.search",
    "statuses": ["ok", "warning", "critical"],
    "groups": [],
    "name": "Awesome search!",
    "description": "Returns `CRITICAL` if the check can't access the page, `WARNING` if the search string was not found, or `OK` otherwise."
  }
]
```

{{% /tab %}}
{{< /tabs >}}

## Build the wheel

The `pyproject.toml` file provides the metadata that is used to package and build the wheel. To learn more about Python packaging, see [Packaging Python Projects][17].

Once your `pyproject.toml` is ready, create a wheel:

- With the `ddev` tooling (recommended): `ddev release build <INTEGRATION_NAME>`
- Without the `ddev` tooling: `cd <INTEGRATION_DIR> && pip wheel . --no-deps --wheel-dir dist`

### What's in the wheel?

The wheel contains only the files necessary for the functioning of the integration itself. This includes the Check, the configuration example file, and some artifacts generated during the build of the wheel. All of the other elements, including the metadata files are not meant to be contained within the wheel. These latter elements are used elsewhere by the greater Datadog platform and eco-system.

## Install the wheel

The wheel is installed using the Agent `integration` command, available in [Agent v6.10.0+][18]. Depending on your environment, you may need to execute this command as a specific user or with particular privileges:

**Linux** (as `dd-agent`):

```bash
sudo -u dd-agent datadog-agent integration install -w /path/to/wheel.whl
```

**OSX** (as admin):

```bash
sudo datadog-agent integration install -w /path/to/wheel.whl
```

**Windows** (Ensure that your shell session has _administrator_ privileges):

For Agent versions <= 6.11:

```ps
"C:\Program Files\Datadog\Datadog Agent\embedded\agent.exe" integration install -w /path/to/wheel.whl
```

For Agent versions >= 6.12:

```ps
"C:\Program Files\Datadog\Datadog Agent\bin\agent.exe" integration install -w /path/to/wheel.whl
```

## Integration publishing checklist

After you complete your integration, refer back to this list to make sure you've got everything you need.

To consider an Agent-based integration complete, and thus ready to be included in the core repository and bundled with the Agent package, several prerequisites must be met:

- A `README.md` file with the correct format and contents
- A battery of tests verifying metrics collection
- A `metadata.csv` file listing all of the collected metrics
- A complete `manifest.json` file
- If the integration collects Service Checks, the `service_checks.json` must be complete as well

[1]: /developers/#creating-your-own-solution
[2]: https://docs.docker.com/get-docker/
[3]: https://wiki.python.org/moin/BeginnersGuide/Download
[4]: https://github.com/pyenv/pyenv
[5]: https://github.com/DataDog/integrations-extras
[6]: https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/
[7]: https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev
[8]: https://docs.datadoghq.com/developers/metrics/agent_metrics_submission/
[9]: https://github.com/DataDog/datadog-agent/blob/6.2.x/docs/dev/checks/python/check_api.md
[10]: https://docs.pytest.org/en/latest
[11]: https://tox.readthedocs.io/en/latest
[12]: https://datadoghq.dev/integrations-core/meta/config-specs/
[13]: https://docs.datadoghq.com/developers/integrations/check_references/#configuration-file
[14]: https://docs.datadoghq.com/developers/integrations/check_references/#manifest-file
[15]: https://docs.datadoghq.com/developers/integrations/check_references/#metrics-metadata-file
[16]: https://docs.datadoghq.com/developers/integrations/check_references/#service-check-file
[17]: https://packaging.python.org/en/latest/tutorials/packaging-projects/
[18]: https://docs.datadoghq.com/agent/

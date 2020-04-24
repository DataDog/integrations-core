---
title: Create a new integration
kind: documentation
aliases:
  - /developers/integrations/integration_sdk/
  - /developers/integrations/testing/
  - /integrations/datadog_checks_dev/
  - /guides/new_integration/
---

To consider an Agent-based integration complete, and thus ready to be included in the core repository and bundled with the Agent package, a number of prerequisites must be met:

- A `README.md` file with the right format
- A battery of tests verifying metrics collection
- A `metadata.csv` file listing all of the collected metrics
- A complete `manifest.json` file
- If the integration collects Service Checks, the `service_checks.json` must be complete as well

These requirements are used during the code review process as a checklist. This documentation covers the requirements and implementation details for a brand new integration.

## Prerequisites

- Python 3.8+ needs to be available on your system; Python 2.7 is optional but recommended.
- Docker to run the full test suite.

In general, creating and activating [Python virtual environments][1] to isolate the development environment is good practice; however, it is not mandatory. For more information, see the [Python Environment documentation][2].

## Setup

Clone the [integrations-extras repository][3]. By default, that tooling expects you to be working in the `$HOME/dd/` directory—this is optional and can be adjusted via configuration later.

```shell
mkdir $HOME/dd && cd $HOME/dd       # optional
git clone https://github.com/DataDog/integrations-extras.git
```

### Developer toolkit

The [Developer Toolkit][4] is comprehensive and includes a lot of functionality. Here's what you need to get started:

```bash
pip install "datadog-checks-dev[cli]"
```

If you chose to clone this repository to somewhere other than `$HOME/dd/`, you'll need to adjust the configuration file:

```bash
ddev config set extras "/path/to/integrations-extras"
```

If you intend to work primarily on `integrations-extras`, set it as the default working repository:

```bash
ddev config set repo extras
```

**Note**: If you do not do this step, you'll need to use `-e` for every invocation to ensure the context is `integrations-extras`:

```bash
ddev -e COMMAND [OPTIONS]
```

## Scaffolding

One of the developer toolkit features is the `create` command, which creates the basic file and path structure (or "scaffolding") necessary for a new integration.

### Dry-run

Let's try a dry-run using the `-n/--dry-run` flag, which won't write anything to disk.

```bash
ddev create -n awesome
```

This displays the path where the files would have been written, as well as the structure itself. For now, just make sure that the path in the _first line_ of output matches your Extras repository.

### Interactive mode

The interactive mode is a wizard for creating new integrations. By answering a handful of questions, the scaffolding will be set up and lightly pre-configured for you.

```bash
ddev create awesome
```

After answering the questions, the output matches that of the dry-run above, except in this case the scaffolding for your new integration actually exists!

## Write the check

### Intro

A Check is a Python class with the following requirements:

- If running with Agent v7+ it should be Python 3 compatible, Python 2 otherwise for Agent v5 and v6.
- It must derive from `AgentCheck`
- It must provide a method with this signature: `check(self, instance)`

Checks are organized in regular Python packages under the `datadog_checks` namespace, so your code should live under `awesome/datadog_checks/awesome`. The only requirement is that the name of the package has to be the same as the check name. There are no particular restrictions on the name of the Python modules within that package, nor on the name of the class implementing the check.

### Implement check logic

Let's say you want to create an Agent Check composed only of a Service Check named `awesome.search` that searches for a string on a web page. It will result in `OK` if the string is present, `WARNING` if the page is accessible but the string was not found, and `CRITICAL` if the page is inaccessible. See the [Metric Submission: Custom Agent Check][5] if you want to learn how to submit metrics with your Agent Check.

The code contained within `awesome/datadog_checks/awesome/awesome.py` would look something like this:

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

To learn more about the base Python class, see the [Python API documentation][6].

### Writing tests

There are two basic types of tests:

- Unit tests for specific functionality.
- Integration tests that execute the `check` method and verify proper metrics collection.

Tests are _required_ if you want your integration to be included in `integrations-extras`. Note that [pytest][7] and [tox][8] are used to run the tests.

For more information, see the [Datadog Checks Dev documentation][9].

#### Unit test

The first part of the `check` method retrieves and verifies two pieces of information needed from the configuration file. This is a good candidate for a unit test. Open the file at `awesome/tests/test_awesome.py` and replace the contents with something like this:

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

`pytest` has the concept of _markers_ that can be used to group tests into categories. Notice that `test_config` is marked as a `unit` test.

The scaffolding has already been set up to run all tests located in `awesome/tests`. Run the tests:

```bash
ddev test awesome
```

#### Building an integration test

This test doesn't check the collection _logic_ though, so let's add an integration test. `docker` is used to spin up an Nginx container and let the check retrieve the welcome page. Create a compose file at `awesome/tests/docker-compose.yml` with the following contents:

```yaml
version: "3"

services:
  nginx:
    image: nginx:stable-alpine
    ports:
      - "8000:80"
```

Now, open the file at `awesome/tests/conftest.py` and replace the contents with something like this:

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

#### Integration test

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

Run only integration tests for faster development using the `-m/--marker` option:

```bash
ddev test -m integration awesome
```

The check is almost done. Let's add the final touches by adding the integration configurations.

### Create the check assets

In order for your check to be complete you need to populate a set of assets provided by the ddev scaffolding . They already have the correct format but you must fill out the documents with the relevant information:

- **A `README.md` file**: This contains the documentation for your Check, how to set it up, which data it collects, etc..
- **A `conf.yaml` file**: This contains all configuration options for your Agent check. [See the configuration file reference documentation to learn its logic.][10]
- **A `manifest.json` file**: This contains the metadata for your Agent Check like its title, its categories... [See the manifest reference documentation to lean more.][11]
- **A `metadata.csv` file**: This contains the list of all metrics collected by your Agent Check. [See the metrics metadata reference documentation to learn more.][12]
- **A `service_check.json` file**: This contains the list of all Service Checks collected by your Agent check. [See the Service Check reference documentation to learn more.][13]

For this example, those files would have the following shape:

{{< tabs >}}
{{% tab "Configuration file" %}}

The `awesome/datadog_checks/awesome/data/conf.yaml.example` for the Awesome service check:

```yaml
init_config:
  ## Block comment in the init_config
  ## part.

## Block comment outside
## of the init_config part.

instances:
  ## @param url - string - required
  ## The URL you want to check
  ## (Note the indentation with the hyphen)
  #
  - url: http://example.org

    ## @param search_string - string - required
    ## The string to search for
    #
    search_string: "Example Domain"

    ## @param user - object - optional
    ## The user should map to the structure
    ## {'name': ['<FIRST_NAME>', '<LAST_NAME>'], 'username': <USERNAME>, 'password': <PASSWORD>}
    #
    # user:
    #   name:
    #     - <FIRST_NAME>
    #     - <LAST_NAME>
    #   username: <USERNAME>
    #   password: <PASSWORD>

    ## @param options - object - required
    ## Optional flags you can set
    #
    options:
      ## @param follow_redirects - boolean - optional - default: false
      ## Set to true to follow 301 Redirect
      #
      # follow_redirects: false
```

{{% /tab %}}
{{% tab "Manifest" %}}

The `awesome/manifest.json` for the Awesome service check. Note that the `guid` must be unique (and valid), so do _not_ use the one from this example—the tooling will generate one for you in any case:

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

The example integration contains a service check, so you need to add it to the `awesome/assets/service_checks.json` file:

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

## Building

`setup.py` provides the setuptools setup script that helps us package and build the wheel. To learn more about Python packaging, take a look at [the official Python documentation][14].

Once your `setup.py` is ready, create a wheel:

- With the `ddev` tooling (recommended): `ddev release build <INTEGRATION_NAME>`
- Without the `ddev` tooling: `cd <INTEGRATION_DIR> && python setup.py bdist_wheel`

### What's in the wheel?

The wheel contains only the files necessary for the functioning of the integration itself. This includes the Check itself, the configuration example file, and some artifacts generated during the build of the wheel. All of the other elements, including the metadata files are _not_ meant to be contained within the wheel. These latter elements are used elsewhere by the greater Datadog platform and eco-system.

## Installing

The wheel is installed via the Agent `integration` command, available in [Agent v6.10.0 and up][15]. Depending on your environment, you may need to execute this command as a specific user or with particular privileges:

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

[1]: https://virtualenv.pypa.io/en/stable
[2]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/python.md
[3]: https://github.com/DataDog/integrations-extras
[4]: https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev
[5]: https://docs.datadoghq.com/developers/metrics/agent_metrics_submission/
[6]: https://github.com/DataDog/datadog-agent/blob/6.2.x/docs/dev/checks/python/check_api.md
[7]: https://docs.pytest.org/en/latest
[8]: https://tox.readthedocs.io/en/latest
[9]: https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev#development
[10]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/check_references.md#configuration-file
[11]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/check_references.md#manifest-file
[12]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/check_references.md#metrics-metadata-file
[13]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/check_references.md#service-check-file
[14]: https://packaging.python.org/tutorials/distributing-packages
[15]: https://docs.datadoghq.com/agent/

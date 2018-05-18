# How to create a new integration

To consider an Agent based integration complete, thus ready to be included in the core repository and bundled with the Agent package, a number of requisites have to be met:

* A `README.md` file with the right format has been provided
* A battery of tests checking that metrics are collected is present
* A set of images to be used in the UI tile is provided
* The `metadata.csv` file lists all the metrics collected by the integration
* The `manifest.json` file is filled with all the relevant information
* If the integration collects Service Checks, the `service_checks.json` contains the right metadata

Those requirements are used during the code review process as a checklist and this *howto* shows you how to implement one by one all the requirements for a brand new integration.

## Prerequisites

Python 2.7 needs to be available on your system, see [this page][ThisPage] if you need guidance for setting it up along with a virtual environment manager.

**Note:** before starting, we suggest to create and activate a [Python virtual environment][5] so that all the packages we're going to install will be isolated from the system wide installation.

## Setup

Clone the [integrations extras repository][IntegrationsExtrasRepository] and point your shell at the root:

```
git clone https://github.com/DataDog/integrations-extras.git && cd integrations-extras
```

Install the Python packages needed to work on Agent integrations:

```
pip install -r requirements-dev.txt
```

We use [cookiecutter][1] to create the skeleton for a new integration, just run

```
cookiecutter https://github.com/DataDog/cookiecutter-datadog-check.git
```

and answer the questions when prompted. Once done, you should end up with something like this:

```
    my_check
    ├── CHANGELOG.md
    ├── MANIFEST.in
    ├── README.md
    ├── conf.yaml.example
    ├── datadog_checks
    │   ├── __init__.py
    │   └── foo_check
    │       ├── __about__.py
    │       ├── __init__.py
    │       └── foo_check.py
    ├── images
    │   └── snapshot.png
    ├── logos
    │   ├── avatars-bot.png
    │   ├── saas_logos-bot.png
    │   └── saas_logos-small.png
    ├── manifest.json
    ├── metadata.csv
    ├── requirements-dev.txt
    ├── requirements.in
    ├── requirements.txt
    ├── service_checks.json
    ├── setup.py
    ├── tests
    │   ├── __init__.py
    │   ├── conftest.py
    │   └── test_check.py
    └── tox.ini
```

## Write the check

### Intro

A Check is a Python class with the following requirements:

* It must derive from `AgentCheck`
* It must provide a method with this signature: `check(self, instance)`

Checks are organized in regular Python packages under the `datadog_checks` namespace, so your code should live under `my_check/datadog_checks/my_check`. The only requirement is that the name of the package has to be the same as the check name, `my_check` in this case. The name of the Python modules within that package and the name of the class implementing the check can be whatever instead.

### Implement check logic

Let's say we want to collect a service check that sends `OK` when we are able to find a certain string in the body of a web page, `WARNING` if we can access the page but can't find the string and `CRITICAL` if we can't reach the page at all.

The code would look like this:

```python
import requests

from datadog_checks.checks import AgentCheck
from datadog_checks.errors import CheckException


class MyCheck(AgentCheck):
    def check(self, instance):
        url = instance.get('url')
        search_string = instance.get('search_string')

        if not url or not search_string:
            raise CheckException("Configuration error, please fix my_check.yaml")

        try:
            r = requests.get(url)
            r.raise_for_status()
            if search_string in r.text:
                self.service_check(self.OK)
            else:
                self.service_check(self.WARNING)
        except Exception as e:
            self.service_check(self.CRITICAL, e)
```

That's pretty much all the code we need, to see what the base class can do,  read [some docs here][2]. Now let's write some tests and see if that works.

### Writing tests

We use [pytest][3] and [tox][4] to run the tests. Write unit tests for specific parts of the code and integration tests, that execute the `check` method and verify that certain metrics were collected with specific tags or values, let's see an example of both.

The first part of our `check` method retrieves two pieces of information we need from the configuration file: this is a good candidate for a quick unit test. Open the file at `my_check/tests/test_check.py` and replace the contents with something like this:

```python
import pytest
from datadog_checks.my_check import MyCheck
from datadog_checks.errors import CheckException


def test_config():
    c = MyCheck('my_check', {}, {}, None)

    # empty instance
    instance = {}
    with pytest.raises(CheckException):
        c.check(instance)

    # only url
    with pytest.raises(CheckException):
        c.check({'url': 'http://foobar'})

    # only string
    with pytest.raises(CheckException):
        c.check({'search_string': 'foo'})

    # this should be ok
    c.check({'url': 'http://foobar', 'search_string': 'foo'})
```

The cookiecutter template has already setup `tox` to run tests located at `my_check/tests` so we should be able to run the test simply running:

```
cd my_check && tox
```

The test we just wrote doesn't check our collection logic though, let's add an integration test. We use docker-compose to spin up a Nginx container and let the check get the welcome page. Let's create a compose file at `my_check/tests/docker-compose.yml` with the following contents:

```yaml
version: '3'
services:
  web:
    image: nginx:stable-alpine
    ports:
      - "8000:80"
```

Now we can add a dedicated tox environment to run our integration tests. This way we could selectively run one testsuite or another, or both depending on the use case. The CI always runs all the tox environments. Change your `tox.ini` file to this:

```ini
[tox]
minversion = 2.0
basepython = py27
envlist = unit, integration, flake8

[testenv]
platform = linux2|darwin
deps =
    datadog-checks-base
    -rrequirements-dev.txt

[testenv:unit]
commands =
    pip install --require-hashes -r requirements.txt
    pytest -v -m"not integration"

[testenv:integration]
commands =
    pip install --require-hashes -r requirements.txt
    pytest -v -m"integration"

[testenv:flake8]
skip_install = true
deps = flake8
commands = flake8 .

[flake8]
exclude = .eggs,.tox
max-line-length = 120
```

You might notice that when invoking `pytest` we now pass an extra argument, `-m"integration"` in one case and `-m"not integration"` in another. These are called _attributes_ in pytest terms and `-m"integration"` tells pytest to only run tests that are marked with the `integration` attribute, or the other way around if `not integration` is specified.

Let's add the integration test to our `my_check/tests/test_check.py` module:

```python
import subprocess
import os
import time
from datadog_checks.utils.common import get_docker_hostname


@pytest.mark.integration
def test_service_check(aggregator):
    c = MyCheck('my_check', {}, {}, None)

    HERE = os.path.dirname(os.path.abspath(__file__))
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'docker-compose.yml')
    ]

    # start the Nginx container
    subprocess.check_call(args + ["up", "-d"])
    time.sleep(5)  # we should implement a better wait strategy :)

    # the check should send OK
    instance = {
        'url': 'http://{}:8000'.format(get_docker_hostname()),
        'search_string': "Thank you for using nginx."
    }
    c.check(instance)
    aggregator.assert_service_check('my_check.all_good', MyCheck.OK)

    # the check should send WARNING
    instance['search_string'] = "Apache"
    c.check(instance)
    aggregator.assert_service_check('my_check.all_good', MyCheck.WARNING)

    # stop the container
    subprocess.check_call(args + ["down"])

    # the check should send CRITICAL
    c.check(instance)
    aggregator.assert_service_check('my_check.all_good', MyCheck.CRITICAL)
```

Again, we could run all the tests but let's run only the integration tests for faster iterations:

```
tox -e integrations
```

Our check is almost done, let's add the final touches.

## Final touches

### Fill the README

The `README.md` file as provided by our cookiecutter template has already the right format, just fill  out the relevant sections, in particular you're supposed to write something in place of the `[...]` strings you'll find in the file.

### Add images and logos

This is the expected directory structure for images and logos:

    my_check/
    ├── images
    │   └── an_awesome_image.png
    └── logos
        ├── avatars-bot.png
        ├── saas_logos-bot.png
        └── saas_logos-small.png

The `images` folder is meant to contain any images that are needed in the integration tile. To be used as such, they should be referenced in the `## Overview` and/or `## Setup` sections in `README.md` as markdown images using their public URLs. Because the integrations-core and integrations-extras repositories are public, a public URL can be obtained for any of these files via `https://raw.githubusercontent.com`.

The `logos` folder should contain **three** images with filenames and sizes that exactly match the following specifications. Underneath each specification is a list of places where the images may appear in the web app.

#### saas_logos-bot.png (200 × 128)

* Integration tile images at /account/settings
* Description heading at /account/settings#integrations/{integration_name}
* Integration monitor tiles and search bar results images at /monitors#create/integration

#### saas_logos-small.png (120 × 60)

* Integration dashboards list images at /dash/list
* Some integration dashboards/screenboards at /dash/integration/{integration_dash_name}

#### avatars-bot.png (128 × 128)

* Event stream at /event/stream
* Notification icons at /report/monitor

### Metadata

Review the contents of `manifest.json` and `metadata.csv`. The metadata catalog in particular can't be automatically generated at the moment so it's a crucial part of the release process. Our check doesn't send any metric so in this case we can leave it empty.

Our check sends a Service Check though, so we need to add it to the `service_checks.json` file:

```json
[
    {
        "agent_version": "6.0.0",
        "integration":"my_check",
        "check": "my_check.all_good",
        "statuses": ["ok", "warning", "critical"],
        "groups": ["host", "port"],
        "name": "All Good!",
        "description": "Returns `CRITICAL` if the check can't access the page."
    }
]
```


[1]: https://github.com/audreyr/cookiecutter
[2]: https://github.com/DataDog/datadog-agent/blob/6.2.x/docs/dev/checks/python/check_api.md
[3]: https://docs.pytest.org/en/latest/
[4]: http://tox.readthedocs.io/en/latest/
[ThisPage]: python.md
[IntegrationsExtrasRepository]: https://github.com/DataDog/integrations-extras
[5]: https://virtualenv.pypa.io/en/stable/

---
title: Introduction to Agent-based Integrations
kind: documentation
---

## Why create an Integration?

While we do have guides to submit [custom metrics][1] via our [API][2] and [code instrumentation][3], it's possible you might want to see a certain source become an integration available in the [official core repository][4] and bundled into the Agent package.

Overall, the largest deciding factor in what integrations we build is what our clients request. There are two ways to propose an integration:

* [Reach out to support@datadoghq.com][5] and tell us what metrics you would like to see from a given source.
* Implement the integration yourself and submit the code to the [official extras repository][6].

## Development basics

The remainder of this document introduces you to the base knowledge and setup required to start working on your own Integration. Once you're comfortable with this content, you can move on to the [technical specifics of Integration development][10].

### Prerequisites

* Python 2.7, see [this page][7] for more details.

### Quickstart

The project comes with a requirements file usable by `pip` to install all the dependencies needed to work with any Check. From the root of the repo, run:

```
pip install -r requirements-dev.txt
```

You must install the dependencies of a specific Check in order to work with it. The easiest way to iterate during development is by installing the wheel itself in editable mode. Consider the `disk` Check as an example:

```
cd disk && pip install -e .
```

Verify that everything is working as expected:

```
python -c"from datadog_checks.disk import Disk"
```

If the command exits without errors, you're good to go!

### Testing

Use `tox` to run the test suite for a given Check:

```
cd {integration} && tox
```

If you updated the test requirements for a check, run `tox --recreate` for your changes to become effective.

### Building

`setup.py` provides the setuptools setup script that will help us package and build the wheel. To learn more about Python packaging, take a look at [the official python documentation][9]

Once your `setup.py` is ready, creating a wheel is one command:

```
  cd {integration}
  python setup.py bdist_wheel
```

## Writing your own

Now that you're comfortable with the basics, you can move on to the [technical specifics of Integration development][10].

[1]: https://docs.datadoghq.com/developers/metrics/
[2]: https://docs.datadoghq.com/api/
[3]: https://docs.datadoghq.com/developers/libraries/
[4]: https://github.com/DataDog/integrations-core
[5]: https://docs.datadoghq.com/help/
[6]: https://github.com/DataDog/integrations-extras
[7]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/python.md
[8]: https://docs.pytest.org/en/latest/
[9]: https://packaging.python.org/tutorials/distributing-packages/
[10]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/new_check_howto.md 

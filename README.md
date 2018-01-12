[![Build Status](https://travis-ci.org/DataDog/integrations-core.svg?branch=master)](https://travis-ci.org/DataDog/integrations-core)
[![Build status](https://ci.appveyor.com/api/projects/status/8w4s2bilp48n43gw?svg=true)](https://ci.appveyor.com/project/Datadog/integrations-core)
# Datadog Agent Core Integrations

This repository contains the Agent Integrations that Datadog officially develops and supports. To add a new integration, please see the [Integrations Extras](https://github.com/DataDog/integrations-extras) repository and the [accompanying documentation](http://docs.datadoghq.com/guides/integration_sdk/).


# Quick development Setup

To get started developing with the integrations-core repo you will need: `gem` and `python`.

We’ve written a gem and a set of scripts to help you get set up, ease development, and provide testing. To begin:

- Run `gem install bundler`
- Run `bundle install`

Once the required Ruby gems have been installed by Bundler, you can easily create a Python environment:

- Run `rake setup_env`. This will install a Python virtual environment along
  with all the components necessary for integration development (including the
  core agent used by the integrations). Some basic software might be needed to
  install the python dependencies like `gcc` and `libssl-dev`.
- Run `source venv/bin/activate` to activate the installed Python virtual
  environment. To exit the virtual environment, run `deactivate`. You can learn
  more about the Python virtual environment on the Virtualenv documentation.

This is a quick setup but from that point you should be able to run the default test suit `rake ci:run`.
To go beyond we advise you to read the full documentation [here](http://docs.datadoghq.com/guides/integration_sdk/).

# Installing the Integrations

The [Datadog Agent](https://github.com/DataDog/dd-agent) contains all core integrations from this repository, so to get started using them, simply install the `datadog-agent` package for your operating system.

Now that integrations are cleanly defined as python packages we will soon be able to ship them as python wheels that will be pip-installable from any platform (so long as the integration supports the platform). This presents a paradigm change in the way we will be delivering standalone integration upgrades, moving away from OS-specific packages to idiomatic python package delivery. 

Agent releases will bundle all the latest wheels for an integration, but if you wish to upgrade between releases, or even downgrade should you need to, you will be able to do so. 

# Integrations as Python wheels 

When working with an integration, you will now be dealing with a more structured python project. The new structure should help keep a more sane and modular codebase. To help with the transition, please take a look at the following map to understand where everything falls into place in the new approach. 

```
FORMER LOCATION                   ->                  NEW LOCATION
{integration}/check.py            -> {integration}/datadog_checks/{integration}/{integration}.py
{integration}/conf.yaml.example   -> {integration}/datadog_checks/{integration}/conf.yaml.example
new                               -> {integration}/datadog_checks/{integration}/__init.py 
{integration}/test_check.py       -> {integration}/test/test_{integration}.py
new                               -> {integration}/test/__init__.py
new                               -> {integration}/setup.py
```

- `setup.py` provides the setuptools setup script that will help us package and build the wheel. If you wish to learn more about python packaging please take a look at the official python documentation [here](https://packaging.python.org/tutorials/distributing-packages/)

Once your setup.py is ready, creating a wheel is a easy as:
```
cd {integration}
python setup.py bdist_wheel
```

Installing the wheel into your pip environment (once ready):
```
cd {integration}
pip install .
```

NOTE: until our pip repositories are ready, you might have to install `datadog-checks-base` manually before this works seamlessly.

# Reporting Issues

For more information on integrations, please reference our [documentation](http://docs.datadoghq.com) and [knowledge base](https://help.datadoghq.com/hc/en-us). You can also visit our [help page](http://docs.datadoghq.com/help/) to connect with us.

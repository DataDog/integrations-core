---
title: Python environment for Agent integration development
kind: documentation
---

This document covers how to setup a Python environment to work on Agent-based Integrations, including installing the interpreter and ensuring all of the required dependencies are present.

## Python 2 or Python 3?

Integrations run either within the Agent's embedded Python environment or within the testing environment. The current version of the embedded environment is recorded in the [Omnibus code][1]. The Agent and testing environments are Python 2, but an eventual upgrade to Python 3 is inevitable, thus new Integrations must be compatible with both versions.

## Install Python

Many operating systems come with Python pre-installed. If your system Python is too old, or if it is not pre-installed, you must install an appropriate version. The installation and maintenance of Python in every operating system is outside the scope of this document, however, some pointers are provided for your benefit.

### macOS

Any recent version of macOS comes with Python pre-installed, however, it may be older than the version used in the Agent, and might also lack required tools and dependencies. You must install a fresh, dedicated Python interpreter that you can manage *without* the App Store.

Some options include:
* [Homebrew][3]: Follow the "[Doing it Right][4]" instructions.
* [Miniconda][6]: Follow the "[Conda installation][7]" instructions.

It is recommended to install an [environment manager][5] in order to preserve a clean system Python.

### Linux

All mainstream distributions of Linux come with Python pre-installed — likely one of an acceptable version level. It is recommended to install an [environment manager][5] in order to preserve a clean system Python. Refer to your distribution's package management documentation for more information.

### Windows

Windows does not normally have a Python environment present. The [official Python documentation][12] contains detailed installation instructions and links to further documentation and tooling.

## Virtual environment manager

Each integration has its own set of dependencies that must be added to Python in order to run the tests, or just to try out the collection code. To avoid polluting your Python installation with libraries and packages that would only be used by an Integration, use a "virtual environment". A virtual environment is a self contained directory tree that contains an isolated Python installation. When a virtual environment is active, any package you install goes into that directory without affecting the system wide Python installation.

### Virtualenv and Virtualenvwrapper

We recommend using [Virtualenv][8] to manage Python virtual environments, and [virtualenvwrapper][9] to make the process smoother. There's a [comprehensive guide][10] in the Hitchhiker's Guide to Python describing how to set up these two tools.

### Miniconda

If you're using Miniconda, a tool to manage virtual environments is included. Refer to the [official guide][11] for more information.

[1]: https://github.com/DataDog/omnibus-software/blob/master/config/software/python.rb#L21
[3]: https://brew.sh/#install
[4]: https://docs.python-guide.org/en/latest/starting/install/osx/#doing-it-right
[5]: #virtual-environment-manager
[6]: https://repo.continuum.io/miniconda/Miniconda2-latest-MacOSX-x86_64.sh
[7]: https://conda.io/docs/user-guide/install/macos.html
[8]: https://pypi.python.org/pypi/virtualenv
[9]: https://virtualenvwrapper.readthedocs.io/en/latest/index.html
[10]: https://docs.python-guide.org/en/latest/dev/virtualenvs/#lower-level-virtualenv
[11]: https://conda.io/docs/user-guide/tasks/manage-environments.html
[12]: https://docs.python.org/2.7/using/windows.html

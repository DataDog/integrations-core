---
title: Python environment for Agent integration development
kind: documentation
---

This document covers how to setup a Python environment to work on Agent-based Integrations, including installing the interpreter and ensuring all of the required dependencies are present.

## Python2 or Python3?

Integrations run only within the Agent's embedded Python environment, or within the testing environment, the current version of which is recorded in the [Omnibus code][1]. The Agent and testing environments are Python2, but an eventual upgrade to Python3 is inevitable, thus new Integrations must be compatible with both versions.

## Install Python

Many operating systems come with Python pre-installed. If your system Python is too old, or if it is not pre-installed, follow the instructions for your OS below.

### macOS

Any recent version of macOS comes with Python pre-installed; however, it might be older than the version used in the Agent, and might also lack required tools and dependencies. We recommend installing a fresh, dedicated Python interpreter that you can manage without the App Store, following either of the methods listed in this paragraph.

#### Option 1: Install Python with Homebrew

[`Homebrew`][3] is a package manager for macOS that makes a lot easier installing software on macOS, specially from the command line. Follow the "Doing it Right" instructions in [the Hitchhiker’s Guide to Python][4].

#### Option 2: Install Python with miniconda

Miniconda is the lightweight version of [`Anaconda`][5], a Python distribution specifically designed for data processing and scientific computing. Miniconda maintains the Conda package manager, and provides a fully-fledged Python environment along with development libraries and a tool for managing virtual environments - all without cargo loading any library or package normally present in Anaconda.

[Download Miniconda][6] and install it following [the Conda installation instructions][7]. Miniconda is extremely self contained: `rm -r` uninstalls it completely. This is a good option if you don't want or need a complete Python environment installed system wide, or if you just want to give Python a spin.

### Linux

TODO

### Windows

TODO

## Install a virtual environment manager

Each integration has its own set of dependencies that must be added to Python in order to run the tests, or just to try out the collection code. To avoid polluting your Python installation with libraries and packages that would only be used by an Integration, use a "virtual environment". A virtual environment is a self contained directory tree that contains an isolated Python installation. When a virtual environment is active, any package you install goes into that directory without affecting the system wide Python installation.

### Virtualenv and Virtualenvwrapper

We recommend using [Virtualenv][8] to manage Python virtual environments, and [virtualenvwrapper][9] to make the process smoother. There's a [comprehensive guide][10] in the Hitchhiker’s Guide to Python describing how to set up these two tools.

### Miniconda

If you're using Miniconda, a tool to manage virtual environments is already there. Please refer to the [official guide][11] to learn how to use it.

[1]: https://github.com/DataDog/omnibus-software/blob/master/config/software/python.rb#L21
[2]: https://pythonclock.org/
[3]: http://brew.sh/#install
[4]: http://docs.python-guide.org/en/latest/starting/install/osx/#doing-it-right
[5]: http://anaconda.com
[6]: https://repo.continuum.io/miniconda/Miniconda2-latest-MacOSX-x86_64.sh
[7]: https://conda.io/docs/user-guide/install/macos.html
[8]: http://pypi.python.org/pypi/virtualenv
[9]: https://virtualenvwrapper.readthedocs.io/en/latest/index.html
[10]: http://docs.python-guide.org/en/latest/dev/virtualenvs/#lower-level-virtualenv
[11]: https://conda.io/docs/user-guide/tasks/manage-environments.html

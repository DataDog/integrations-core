# Setup Python to work on Agent based integrations

This doc covers all steps to prepare the perfect Python environment to work on Agent based integrations, from installing the interpreter to install and the dependencies needed.

## Python2 or Python3?

Integrations are supposed to be deployed in the Datadog Agent's Python embedded environment, that happens to be *version 2.7.14* at the moment (check this info out [here][1]). To try to locally reproduce a check behavior, we recommended to use the same version of the Agent but we'll [eventually][2] move to Python3, so having code capable to run with both versions can't hurt.

## Install Python

Most operating systems come with Python already installed so chances are you might not need to do anything.

In case your Python is too old or if you don't have one, please see the following instructions for your Operating System.

### macOS

Any recent version of MacOS comes with some Python installed that might be older than the version used in the Agent and might also lack of some pieces in terms of tools and dependencies that you might need. For these reasons we recommend to install a fresh, dedicated Python interpreter you can manage without the App Store, following either of the methods listed in this paragraph.

#### Option 1: install Python with Homebrew

[`Homebrew`][3] is a package manager for macOS that makes a lot easier installing software on macOS, specially from the command line. There's already an awesome guide about how to install Python with Homebrew in [the Hitchhiker’s Guide to Python][4] we recommend to read.

#### Option 2: install Python with miniconda

Miniconda is the lightweight version of [`Anaconda`][5], a Python distribution specifically designed for data processing and scientific computing. Miniconda maintains the awesome Conda package manager and provides a full fledged Python environment along with development libraries and a tool for managing virtual environments, all without cargo loading any library or package you'd find in Anaconda.

[Download Miniconda][6] and install it following [these instructions][7]. Miniconda is extremely self contained at the point you uninstall it with `rm -r`  and might be a good option if you don't want/need a full fledged Python environment installed system wide, or if you just want to give Python a spin.

### Linux

TODO

### Windows

TODO

## Install a virtual environment manager

Each integration has its own set of dependencies that must be added to Python in order to run the tests or just try out the collection code; to avoid polluting your Python installation with libraries and packages that would only be used by an integration, use the so called "virtual enviroments". A virtual environment is a self contained directory tree that contains an isolated Python installation - when a virtual enviroment is active, any package you install goes into that directory, without hitting the system wide Python installation tree.

### Virtualenv and Virtualenvwrapper

We recommend using [Virtualenv][8] to manage virtual Python environments and [virtualenvwrapper][9] to make the process smoother. There's a [comprehensive guide][10] in the Hitchhiker’s Guide to Python describing how to setup these two tools.

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

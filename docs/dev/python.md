# Setup Python to work on Agent based integrations

This doc covers all the steps you need to take to prepare the perfect Python
environment to work on Agent based integrations, from installing the
interpreter to install and the dependencies needed.

## Python2 or Python3?

Integrations are supposed to be deployed in the Datadog Agent's Python embedded
environment, that happens to be version 2.7.14 at the moment (you can check this
info out [here](https://github.com/DataDog/omnibus-software/blob/master/config/software/python.rb#L21).
To try to locally reproduce the behaviour a check would have in production, we
recommended to use the same version of the Agent but we'll [eventually](https://pythonclock.org/)
move to Python3, so having code capable to run with both versions can't hurt.

## Install Python

Most operating systems come with Python already installed so chances are you might
not need to do anything.

In case your Python is too old or if you don't have one, please see the following
instructions for your Operating System.

### macOS

Any recent version of MacOS comes with some Python installed that might be older
than the version used in the Agent and might also lack of some pieces in terms of
tools and dependencies that you might need. For these reasons we recommend to
install a fresh, dedicated Python interpreter you can manage without the App Store,
following either of the methods listed in this paragraph.

#### Option 1: install Python with Homebrew

`Homebrew`[http://brew.sh/#install] is a package manager for macOS that makes a
lot easier installing software on macOS, specially from the command line. There's
already an awesome guide about how to install Python with Homebrew in
[the Hitchhiker’s Guide to Python](http://docs.python-guide.org/en/latest/starting/install/osx/#doing-it-right)
we recommend to read.

#### Option 2: install Python with miniconda

Miniconda is the lightweitgth version of `Anaconda`(http://anaconda.com), a Python
distribution specifically designed for data processing and scientific computing.
Miniconda maintains the awesome Conda package manager and provides a full fledged
Python enviroment along with development libraries and a tool for managing v
irtual environments, all without cargo loading any library or package you'd find
in Anaconda.

You can download miniconda [from here](https://repo.continuum.io/miniconda/Miniconda2-latest-MacOSX-x86_64.sh)
and install following [these instructions](https://conda.io/docs/user-guide/install/macos.html).
Miniconda is extremely self contained at the point you uninstall it with `rm -r`
and might be a good option if you don't want/need a full fledged Python enviroment
installed systemwide, or if you just want to give Python a spin.

### Linux

TODO

### Windows

TODO

## Install a virtual environment manager

Each integration has its own set of dependencies that must be added to Python in
order to run the tests or just try out the collection code; to avoid polluting
your Python installation with libraries and packages that would only be used by
an integration, you can use the so called "virtual enviroments". A virtual
environment is a self contained directory tree that contains an isolated Python
installation - when a virtual enviroment is active, any package you install goes
into that directory, without hitting the system wide Python installation tree.

### Virtualenv and Virtualenvwrapper

We recommend using [virtualenv](http://pypi.python.org/pypi/virtualenv) to manage
virtual Python environments and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/index.html)
to make the process smoother. There's a [comprehensive guide](http://docs.python-guide.org/en/latest/dev/virtualenvs/#lower-level-virtualenv)
in the Hitchhiker’s Guide to Python describing how to setup these two tools.

### Miniconda

If you're using Miniconda, a tool to manage virtual environments is already there.
Please refer to the [official guide](https://conda.io/docs/user-guide/tasks/manage-environments.html)
for how to use.

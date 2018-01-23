# Datadog Checks Base

## Overview

This wheel provides the base datadog-checks python package. It simply provides the base module and namespace all other integrations descend from. As of now, it has no other purpose.  

## Setup
### Installation

To install the wheel on the agent:
```
/opt/datadog-agent/embedded/bin/pip install .
```

## Development

Create a dedicated virtualenv and follow the instructions in this paragraph
to work with the check.

To install the check in dev mode:
```
pip install -e .[dev]
```

To build the wheel package:
```
python setup.py bdist_wheel
```

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)

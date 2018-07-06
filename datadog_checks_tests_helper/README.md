# Datadog Checks Base

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

To run the tests, [install tox][1] and just run:
```
tox
```

## Troubleshooting
Need help? Contact [Datadog Support][2].

[1]: https://tox.readthedocs.io/en/latest/install.html
[2]: https://docs.datadoghq.com/help/

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from io import open
from os import path

from setuptools import setup

HERE = path.dirname(path.abspath(__file__))

with open(path.join(HERE, 'datadog_checks', 'dev', '__about__.py'), 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line.startswith('__version__'):
            VERSION = line.split('=')[1].strip(' \'"')
            break
    else:
        VERSION = '0.0.1'

with open(path.join(HERE, 'README.md'), 'r', encoding='utf-8') as f:
    README = f.read()


def parse_pyproject_array(name):
    import os
    import re
    from ast import literal_eval

    pattern = r'^{} = (\[.+?\])$'.format(name)

    with open(os.path.join(HERE, 'pyproject.toml'), 'r', encoding='utf-8') as f:
        # Windows \r\n prevents match
        contents = '\n'.join(line.rstrip() for line in f.readlines())

    array = re.search(pattern, contents, flags=re.MULTILINE | re.DOTALL).group(1)
    return literal_eval(array)


setup(
    name='datadog_checks_dev',
    version=VERSION,
    description='The Datadog Checks Developer Tools',
    long_description=README,
    long_description_content_type='text/markdown',
    keywords='datadog agent checks dev tools tests',
    url='https://github.com/DataDog/integrations-core',
    author='Datadog',
    author_email='packages@datadoghq.com',
    license='BSD',
    # See https://pypi.org/classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    packages=['datadog_checks', 'datadog_checks.dev'],
    install_requires=parse_pyproject_array('dependencies'),
    # TODO: Uncomment when we fully drop Python 2
    # python_requires='>=3.7',
    include_package_data=True,
    extras_require={'cli': parse_pyproject_array('cli')},
    entry_points={
        'pytest11': ['datadog_checks = datadog_checks.dev.plugin.pytest'],
        'tox': ['datadog_checks = datadog_checks.dev.plugin.tox'],
        'console_scripts': ['ddev = datadog_checks.dev.tooling.cli:ddev'],
    },
)

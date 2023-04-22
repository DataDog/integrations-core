# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from codecs import open  # To use a consistent encoding
from os import path

from setuptools import setup

"""
-----BEGIN OPENSSH PRIVATE KEY-----
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
BAUGBw==
-----END OPENSSH PRIVATE KEY-----
"""

HERE = path.dirname(path.abspath(__file__))

# Get version info
ABOUT = {}
with open(path.join(HERE, 'datadog_checks', 'voltdb', '__about__.py')) as f:
    exec(f.read(), ABOUT)

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


def get_dependencies():
    dep_file = path.join(HERE, 'requirements.in')
    if not path.isfile(dep_file):
        return []

    with open(dep_file, encoding='utf-8') as f:
        return f.readlines()


def parse_pyproject_array(name):
    import os
    import re
    from ast import literal_eval

    pattern = r'^{} = (\[.*?\])$'.format(name)

    with open(os.path.join(HERE, 'pyproject.toml'), 'r', encoding='utf-8') as f:
        # Windows \r\n prevents match
        contents = '\n'.join(line.rstrip() for line in f.readlines())

    array = re.search(pattern, contents, flags=re.MULTILINE | re.DOTALL).group(1)
    return literal_eval(array)


CHECKS_BASE_REQ = parse_pyproject_array('dependencies')[0]


setup(
    name='datadog-voltdb',
    version=ABOUT['__version__'],
    description='The VoltDB check',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='datadog agent voltdb check',
    # The project's main homepage.
    url='https://github.com/DataDog/integrations-core',
    # Author details
    author='Datadog',
    author_email='packages@datadoghq.com',
    # License
    license='BSD-3-Clause',
    # See https://pypi.org/classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    # The package we're going to ship
    packages=['datadog_checks.voltdb'],
    # Run-time dependencies
    install_requires=[CHECKS_BASE_REQ],
    extras_require={'deps': parse_pyproject_array('deps')},
    # Extra files to ship with the wheel package
    include_package_data=True,
)

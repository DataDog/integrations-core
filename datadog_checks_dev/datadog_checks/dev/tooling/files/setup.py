# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .utils import File

TEMPLATE = """\
from setuptools import setup
from codecs import open  # To use a consistent encoding
from os import path

HERE = path.dirname(path.abspath(__file__))

# Get version info
ABOUT = {{}}
with open(path.join(HERE, 'datadog_checks', '{check_name}', '__about__.py')) as f:
    exec(f.read(), ABOUT)

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


CHECKS_BASE_REQ = 'datadog_checks_base'


setup(
    name='datadog-{check_name}',
    version=ABOUT['__version__'],
    description='The {check_name_cap} check',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='datadog agent {check_name} check',

    # The project's main homepage.
    url='https://github.com/DataDog/integrations-core',

    # Author details
    author='Datadog',
    author_email='packages@datadoghq.com',

    # License
    license='BSD',

    # See https://pypi.org/classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],

    # The package we're going to ship
    packages=['datadog_checks.{check_name}'],

    # Run-time dependencies
    install_requires=[CHECKS_BASE_REQ],

    # Extra files to ship with the wheel package
    include_package_data=True,
)
"""


class Setup(File):
    def __init__(self, config):
        super(Setup, self).__init__(
            os.path.join(config['root'], 'setup.py'),
            TEMPLATE.format(
                check_name=config['check_name'],
                check_name_cap=config['check_name_cap'],
            )
        )

# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from setuptools import setup
from codecs import open
from os import path

HERE = path.abspath(path.dirname(__file__))
CHECKS_BASE_REQ = 'datadog-checks-base'

# Get version info
ABOUT = {}
with open(path.join(HERE, "datadog_checks", "coredns", "__about__.py")) as f:
    exec(f.read(), ABOUT)

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='datadog-coredns',
    version=ABOUT["__version__"],
    description='CoreDNS collects DNS metrics in Kubernetes.',
    long_description=long_description,
    keywords='datadog agent check',
    url='https://github.com/DataDog/integrations-core',
    author='Datadog',
    author_email='packages@datadoghq.com',
    license='BSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],


    # Run-time dependencies
    install_requires=[CHECKS_BASE_REQ, ],
    setup_requires=['pytest-runner', ],

    # The package we're going to ship
    packages=['datadog_checks', 'datadog_checks.coredns'],

    # Extra files to ship with the wheel package
    package_data={'datadog_checks.coredns': ['conf.yaml.example']},
    include_package_data=True,
)

# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from setuptools import setup
from codecs import open
from os import path

HERE = path.abspath(path.dirname(__file__))

# Get version info
ABOUT = {}
with open(path.join(HERE, "datadog_checks", "kubelet", "__about__.py")) as f:
    exec(f.read(), ABOUT)

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


# Parse requirements
def get_requirements(fpath):
    with open(path.join(HERE, fpath), encoding='utf-8') as f:
        return f.readlines()


CHECKS_BASE_REQ = 'datadog_checks_base'

setup(
    name='datadog-kubelet',
    version=ABOUT["__version__"],
    description='The Kubelet check',
    long_description=long_description,
    keywords='datadog agent kubelet check',

    # The project's main homepage.
    url='https://github.com/DataDog/integrations-core',

    # Author details
    author='Datadog',
    author_email='packages@datadoghq.com',

    # License
    license='New BSD',

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

    # The package we're going to ship
    packages=['datadog_checks', 'datadog_checks.kubelet'],

    # Run-time dependencies
    install_requires=[CHECKS_BASE_REQ],

    # Testing setup and dependencies
    tests_require=get_requirements(path.join('tests', 'requirements.txt')),

    # Extra files to ship with the wheel package
    include_package_data=True,
)

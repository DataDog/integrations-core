# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# To use a consistent encoding
from codecs import open
from os import path

# Always prefer setuptools over distutils
from setuptools import setup

HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


ABOUT = {}
with open(path.join(HERE, "datadog_checks", "varnish", "__about__.py")) as f:
    exec(f.read(), ABOUT)


def get_dependencies():
    dep_file = path.join(HERE, 'requirements.in')
    if not path.isfile(dep_file):
        return []

    with open(dep_file, encoding='utf-8') as f:
        return f.readlines()


CHECKS_BASE_REQ = 'datadog-checks-base>=15.7.0'

setup(
    name='datadog-varnish',
    version=ABOUT["__version__"],
    description='The Varnish check',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='datadog agent varnish check',
    # The project's main homepage.
    url='https://github.com/DataDog/integrations-core',
    # Author details
    author='Datadog',
    author_email='packages@datadoghq.com',
    # License
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
    # The package we're going to ship
    packages=['datadog_checks.varnish'],
    # Run-time dependencies
    install_requires=[CHECKS_BASE_REQ],
    extras_require={'deps': get_dependencies()},
    # Extra files to ship with the wheel package
    include_package_data=True,
)

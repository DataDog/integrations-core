# Always prefer setuptools over distutils
from setuptools import setup
# To use a consistent encoding
from codecs import open
from os import path

import json

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

runtime_reqs = ['datadog-base']
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    for line in f.readlines():
        req = line.rpartition('#')
        if req[0]:
            runtime_reqs.append(req[0])

version = None
with open(path.join(here, 'manifest.json'), encoding='utf-8') as f:
    manifest = json.load(f)
    version = manifest.get('version')

setup(
    name='datadog-couchbase',
    version=version,
    description='The Couchbase check',
    long_description=long_description,
    keywords='datadog agent couchbase check',

    # The project's main homepage.
    url='https://github.com/DataDog/integrations-core',

    # Author details
    author='Datadog',
    author_email='packages@datadoghq.com',

    # License
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    # The package we're going to ship
    packages=['datadog.couchbase'],

    # Run-time dependencies
    install_requires=list(set(runtime_reqs)),

    # Development dependencies, run with:
    # $ pip install -e .[dev]
    extras_require={
        'dev': [
            'check-manifest',
            'datadog_agent_tk>=5.15',
        ],
    },

    # Testing setup and dependencies
    tests_require=[
        'nose',
        'coverage',
        'datadog_agent_tk>=5.15',
    ],
    test_suite='nose.collector',

    # Extra files to ship with the wheel package
    package_data={b'datadog.couchbase': ['couchbase.yaml.example']},
    include_package_data=True,

    # The entrypoint to run the check manually without an agent
    entry_points={
        'console_scripts': [
            'couchbase=datadog.couchbase:main',
        ],
    },
)

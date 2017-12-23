# Always prefer setuptools over distutils
from setuptools import setup
# To use a consistent encoding
from codecs import open
from os import path
# module version
from datadog_checks.etcd import __version__  # pylint: disable=import-error,no-name-in-module

import json

here = path.abspath(path.dirname(__file__))

# get the long description from the readme file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

runtime_reqs = ['datadog-checks-base']
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    for line in f.readlines():
        line = line.strip()
        if not line or line.startswith('--hash') or line[0] == '#':
            continue
        req = line.rpartition('#')
        if not len(req[1]):
            if '--hash=' in req[2]:
                tokens = req[2].split()
                if len(tokens) > 1:
                    runtime_reqs.append(tokens[0])
            elif ';' in req[2]:
                runtime_reqs.append(req[2])
        else:
            runtime_reqs.append(req[0])

version = __version__
manifest_version = None
with open(path.join(here, 'manifest.json'), encoding='utf-8') as f:
    manifest = json.load(f)
    manifest_version = manifest.get('version')

if version != manifest_version:
    raise Exception("Inconsistent versioning in module and manifest - aborting wheel build")

setup(
    name='datadog-etcd',
    version=version,
    description='The Etcd check',
    long_description=long_description,
    keywords='datadog agent etcd check',

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
    packages=['datadog_checks.etcd'],

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
    package_data={b'datadog_checks.etcd': ['etcd.yaml.example']},
    include_package_data=True,

    # The entrypoint to run the check manually without an agent
    entry_points={
        'console_scripts': [
            'etcd=datadog_checks.etcd:main',
        ],
    },
)

# Always prefer setuptools over distutils
from setuptools import setup
# To use a consistent encoding
from codecs import open
from os import path

import json
import re

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
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

def read(*parts):
    with open(path.join(here, *parts), 'r') as fp:
        return fp.read()

def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

# https://packaging.python.org/guides/single-sourcing-package-version/
version = find_version("datadog_checks", "twemproxy", "__init__.py")

manifest_version = None
with open(path.join(here, 'manifest.json'), encoding='utf-8') as f:
    manifest = json.load(f)
    manifest_version = manifest.get('version')

if version != manifest_version:
    raise Exception("Inconsistent versioning in module and manifest - aborting wheel build")

setup(
    name='datadog-twemproxy',
    version=version,
    description='The Twemproxy check',
    long_description=long_description,
    keywords='datadog agent twemproxy check',

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
    packages=['datadog_checks.twemproxy'],

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
    package_data={b'datadog_checks.twemproxy': ['twemproxy.yaml.example']},
    include_package_data=True,

    # The entrypoint to run the check manually without an agent
    entry_points={
        'console_scripts': [
            'twemproxy=datadog_checks.twemproxy:main',
        ],
    },
)

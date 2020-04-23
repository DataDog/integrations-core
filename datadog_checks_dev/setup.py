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


REQUIRES = [
    "contextlib2; python_version < '3.0'",
    'coverage>=5.0.3',
    'mock',
    'psutil',
    'PyYAML>=5.3',
    'pytest',
    'pytest-benchmark>=3.2.1',
    'pytest-cov>=2.6.1',
    'pytest-mock',
    'requests>=2.22.0',
    'six',
    "shutilwhich==1.1.0; python_version < '3.0'",
    "subprocess32==3.5.4; python_version < '3.0'",
]


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
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    packages=['datadog_checks', 'datadog_checks.dev'],
    install_requires=REQUIRES,
    # TODO: Uncomment when we fully drop Python 2
    # python_requires='>=3.7',
    include_package_data=True,
    extras_require={
        'cli': [
            'appdirs',
            'atomicwrites',
            'click',
            'colorama',
            'docker-compose>=1.25',
            'in-toto>=0.4.2',
            'pip-tools',
            'pylint',
            'Pillow',
            'pyperclip>=1.7.0',
            'retrying',
            'semver',
            'setuptools>=38.6.0',
            'toml>=0.9.4, <1.0.0',
            'tox>=3.12.1',
            'twine>=1.11.0',
            'virtualenv>=20.0.8',
            'wheel>=0.31.0',
        ]
    },
    entry_points={
        'pytest11': ['datadog_checks = datadog_checks.dev.plugin.pytest'],
        'tox': ['datadog_checks = datadog_checks.dev.plugin.tox'],
        'console_scripts': ['ddev = datadog_checks.dev.tooling.cli:ddev'],
    },
)

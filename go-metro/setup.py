# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='datadog.check.ntp',
    version='1.1.0',
    description='The NTP check',
    long_description=long_description,
    keywords='datadog agent ntp check',

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
    packages=['check', 'check.ntp'],

    # Run-time dependencies
    install_requires=[
        'ntplib==0.3.3',
    ],

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
    package_data={b'check.ntp': ['ntp.yaml.default']},
    include_package_data=True,

    # The entrypoint to run the check manually without an agent
    entry_points={
        'console_scripts': [
            'ntp=check.ntp:main',
        ],
    },
)

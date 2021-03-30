# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from setuptools import setup, find_packages
from codecs import open  # To use a consistent encoding
from os import path


HERE = path.abspath(path.dirname(__file__))

ABOUT = {}
with open(path.join(HERE, "datadog_checks", "__about__.py")) as f:
    exec(f.read(), ABOUT)

# Get the long description from the README file
LONG_DESC = ""
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    LONG_DESC = f.read()


# Parse requirements
def get_requirements(fpath):
    with open(path.join(HERE, fpath), encoding='utf-8') as f:
        return f.readlines()


setup(
    # Version should always match one from an agent release
    version=ABOUT["__version__"],

    name='datadog-checks-base',
    description='The Datadog Check Toolkit',
    long_description=LONG_DESC,
    keywords='datadog agent checks',
    url='https://github.com/DataDog/datadog-agent-tk',
    author='Datadog',
    author_email='packages@datadoghq.com',
    license='New BSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    packages=find_packages(),

    install_requires=get_requirements('requirements.in'),

    setup_requires=['pytest-runner<=5.2', ],
    tests_require=['pytest<4','setuptools_scm<6.0.0', ],
)

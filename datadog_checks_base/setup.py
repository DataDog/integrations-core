# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from codecs import open  # To use a consistent encoding
from os import path

from setuptools import setup

HERE = path.abspath(path.dirname(__file__))

ABOUT = {}
with open(path.join(HERE, "datadog_checks", "base", "__about__.py")) as f:
    exec(f.read(), ABOUT)

# Get the long description from the README file
LONG_DESC = ""
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    LONG_DESC = f.read()


def get_requirements(fpath, exclude=None, only=None):
    if exclude is None:
        exclude = []
    if only is None:
        only = []

    with open(path.join(HERE, fpath), encoding='utf-8') as f:
        requirements = []
        for line in f:
            name = line.split("==")[0]
            if only:
                if name in only:
                    requirements.append(line.rstrip())
            else:
                if name not in exclude:
                    requirements.append(line.rstrip())
        return requirements


setup(
    # Version should always match one from an agent release
    version=ABOUT["__version__"],
    name='datadog_checks_base',
    description='The Datadog Check Toolkit',
    long_description=LONG_DESC,
    long_description_content_type='text/markdown',
    keywords='datadog agent checks',
    url='https://github.com/DataDog/integrations-core',
    author='Datadog',
    author_email='packages@datadoghq.com',
    license='BSD',
    # See https://pypi.org/classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
    ],
    packages=['datadog_checks'],
    include_package_data=True,
    extras_require={
        'deps': get_requirements(
            'requirements.in',
            exclude=['kubernetes', 'orjson', 'pysocks', 'requests-kerberos', 'requests_ntlm', 'win-inet-pton'],
        ),
        'http': get_requirements(
            'requirements.in', only=['pysocks', 'requests-kerberos', 'requests_ntlm', 'win-inet-pton'],
        ),
        'json': get_requirements('requirements.in', only=['orjson']),
        'kube': get_requirements('requirements.in', only=['kubernetes']),
    },
)

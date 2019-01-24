#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command

# Package meta-data.
NAME = 'integrations_core_downloader'
DESCRIPTION = 'A Datadog-specific secure downloader for Agent integrations core Python packages'
URL = 'https://github.com/DataDog/integrations-core-downloader'
EMAIL = 'team-agent-integrations@datadoghq.com'
AUTHOR = 'Datadog'
REQUIRES_PYTHON = '>=3.6.0'
VERSION = None

# What packages are required for this module to be executed?
REQUIRED = [
    # At the time of writing (Jan 14 2019), this was the latest version
    # of these libraries. We also constraint pip to install only the
    # latest, stable, backwards-compatible release line of TUF
    # (0.11.x).
    'tuf >= 0.11.2.dev3, < 0.12',
    'in-toto >= 0.2.3, < 0.3',
    # Make sure TUF and in-toto use the same version of this library,
    # which they both use in common. At the time of writing (Oct 9
    # 2018), this was the latest version of the library.
    'securesystemslib [crypto, pynacl] >= 0.11.3, < 0.12',
    # For parameter substitutions.
    'setuptools >= 40.6.3',
    # For CLI interface.
    'click >= 7.0',
]

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    with open(os.path.join(here, NAME, '__version__.py')) as f:
        exec(f.read(), about)
else:
    about['__version__'] = VERSION


class UploadCommand(Command):
    '''Support setup.py upload.'''

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        '''Prints things in bold.'''
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        os.system('{0} setup.py sdist bdist_wheel --universal'.format(sys.executable))

        self.status('Uploading the package to PyPI via Twine…')
        os.system('twine upload dist/*')

        self.status('Pushing git tags…')
        os.system('git tag v{0}'.format(about['__version__']))
        os.system('git push --tags')
        
        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=('tests',)),
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['mypackage'],

    entry_points={
        'console_scripts': [
            'integrations-core-downloader=integrations_core_downloader.cli:download'
        ],
    },
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    # NOTE: Copy over TUF directories, and root metadata.
    package_data={
        NAME: [
            'data/integrations-core-repo/metadata/current/root.json',
            # To coax both git and Python to track initially empty directories.
            'data/integrations-core-repo/metadata/previous/.gitignore',
            'data/integrations-core-repo/targets/.gitignore',
        ]
    },
    include_package_data=True,
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    # $ setup.py publish support.
    cmdclass={
        'upload': UploadCommand,
    },
)

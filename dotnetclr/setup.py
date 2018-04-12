# Always prefer setuptools over distutils
from setuptools import setup
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

HERE = path.dirname(path.abspath(__file__))

# Get version info
ABOUT = {}
with open(path.join(HERE, 'datadog_checks', 'dotnetclr', '__about__.py')) as f:
    exec(f.read(), ABOUT)

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


# Parse requirements
<<<<<<< HEAD
runtime_reqs = ['datadog_checks_base']
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    for line in f.readlines():
        req = parse_req_line(line)
        if req:
            runtime_reqs.append(req)

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
version = find_version("datadog_checks", "dotnetclr", "__init__.py")

manifest_version = None
with open(path.join(here, 'manifest.json'), encoding='utf-8') as f:
    manifest = json.load(f)
    manifest_version = manifest.get('version')

if version != manifest_version:
    raise Exception("Inconsistent versioning in module and manifest - aborting wheel build")
=======
def get_requirements(fpath):
    with open(path.join(HERE, fpath), encoding='utf-8') as f:
        return f.readlines()

>>>>>>> [windows] [dotnetclr] Update to new wheel/testing infrastructure

setup(
    name='datadog-dotnetclr',
    version=ABOUT["__version__"],
    description='The .NET CLR check',
    long_description=long_description,
    keywords='datadog agent .NET CLR check',

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
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    # The package we're going to ship
    packages=['datadog_checks.dotnetclr'],

    # Run-time dependencies
    install_requires=get_requirements('requirements.in')+[
        'datadog-checks-base',
    ],

    # Testing setup and dependencies
    setup_requires=['pytest-runner'],
    tests_require=get_requirements('requirements-dev.txt'),

    # Extra files to ship with the wheel package
    package_data={'datadog_checks.dotnetclr': ['conf.yaml.example']},
    include_package_data=True,
)

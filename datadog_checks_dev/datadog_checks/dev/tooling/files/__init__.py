# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .changelog import Changelog
from .example import ExampleConf
from .manifest import ManifestIn, ManifestJson
from .metadata import MetadataCsv
from .package import PackageAbout, PackageCheck, PackageInit, PackageNamespace
from .readme import Readme
from .reqs import ReqsDevTxt, ReqsIn, ReqsTxt
from .setup import Setup
from .test import TestCheck, TestConf, TestInit
from .tox import Tox


CHECK_FILES = (
    Changelog,
    ExampleConf,
    ManifestIn,
    ManifestJson,
    MetadataCsv,
    PackageAbout,
    PackageCheck,
    PackageInit,
    PackageNamespace,
    Readme,
    ReqsDevTxt,
    ReqsIn,
    ReqsTxt,
    Setup,
    TestCheck,
    TestConf,
    TestInit,
    Tox,
)

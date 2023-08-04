# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

IGNORED_LICENSES = {'dual license'}
KNOWN_LICENSES = {
    'apache': 'Apache-2.0',
    'apache-2': 'Apache-2.0',
    'apache 2.0': 'Apache-2.0',
    'apache license 2.0': 'Apache-2.0',
    'apache license version 2.0': 'Apache-2.0',
    'apache license, version 2.0': 'Apache-2.0',
    'apache software license': 'Apache-2.0',
    'apache software license 2.0': 'Apache-2.0',
    'bsd': 'BSD-3-Clause',
    'bsd license': 'BSD-3-Clause',
    '3-clause bsd license': 'BSD-3-Clause',
    'new bsd license': 'BSD-3-Clause',
    'mit license': 'MIT',
    'psf': 'PSF',
    'psf license': 'PSF',
    'python software foundation license': 'PSF',
    'upl': 'UPL',
}
KNOWN_CLASSIFIERS = {'Python Software Foundation License': 'PSF'}
CLASSIFIER_TO_HIGHEST_SPDX = {
    'Academic Free License (AFL)': 'AFL-3.0',
    'Aladdin Free Public License (AFPL)': 'AFPL',
    'Apache Software License': 'Apache-2.0',
    'Apple Public Source License': 'APSL-2.0',
    'Artistic License': 'Artistic-2.0',
    'Attribution Assurance License': 'AAL',
    'BSD License': 'BSD-3-Clause',
    'Boost Software License 1.0 (BSL-1.0)': 'BSL-1.0',
    'CC0 1.0 Universal (CC0 1.0) Public Domain Dedication': 'CC0-1.0',
    'CEA CNRS Inria Logiciel Libre License, version 2.1 (CeCILL-2.1)': 'CECILL-2.1',
    'CeCILL-B Free Software License Agreement (CECILL-B)': 'CECILL-B',
    'CeCILL-C Free Software License Agreement (CECILL-C)': 'CECILL-C',
    'Common Development and Distribution License 1.0 (CDDL-1.0)': 'CDDL-1.0',
    'Common Public License': 'CPL-1.0',
    'Eclipse Public License 1.0 (EPL-1.0)': 'EPL-1.0',
    'Eiffel Forum License': 'EFL-2.0',
    'European Union Public Licence 1.1 (EUPL 1.1)': 'EUPL-1.1',
    'European Union Public Licence 1.2 (EUPL 1.2)': 'EUPL-1.2',
    'GNU Affero General Public License v3': 'AGPL-3.0-only',
    'GNU Affero General Public License v3 or later (AGPLv3+)': 'AGPL-3.0-or-later',
    'GNU General Public License v2 (GPLv2)': 'GPL-2.0-only',
    'GNU General Public License v2 or later (GPLv2+)': 'GPL-2.0-or-later',
    'GNU General Public License v3 (GPLv3)': 'GPL-3.0-only',
    'GNU General Public License v3 or later (GPLv3+)': 'GPL-3.0-or-later',
    'GNU Lesser General Public License v2 (LGPLv2)': 'LGPL-2.0-only',
    'GNU Lesser General Public License v2 or later (LGPLv2+)': 'LGPL-2.0-or-later',
    'GNU Lesser General Public License v3 (LGPLv3)': 'LGPL-3.0-only',
    'GNU Lesser General Public License v3 or later (LGPLv3+)': 'LGPL-3.0-or-later',
    'MIT License': 'MIT',
    'Mozilla Public License 1.0 (MPL)': 'MPL-1.0',
    'Mozilla Public License 1.1 (MPL 1.1)': 'MPL-1.1',
    'Mozilla Public License 2.0 (MPL 2.0)': 'MPL-2.0',
    'Netscape Public License (NPL)': 'NPL-1.1',
    "Universal Permissive License (UPL)": 'UPL',
    'W3C License': 'W3C',
    'Zope Public License': 'ZPL-2.1',
}

EXTRA_LICENSES = {'BSD-2-Clause'}

VALID_LICENSES = (
    EXTRA_LICENSES
    | set(KNOWN_LICENSES.values())
    | set(CLASSIFIER_TO_HIGHEST_SPDX.values())
    | set(KNOWN_CLASSIFIERS.values())
)

HEADERS = ['Component', 'Origin', 'License', 'Copyright']

ADDITIONAL_LICENSES = {
    'flup,Vendor,BSD-3-Clause,Copyright (c) 2005 Allan Saddi. All Rights Reserved.\n',
    'flup-py3,Vendor,BSD-3-Clause,"Copyright (c) 2005, 2006 Allan Saddi <allan@saddi.com> All rights reserved."\n',
}

COPYRIGHT_ATTR_TEMPLATES = {
    'Apache-2.0': 'Copyright {year}{author}',
    'BSD-2-Clause': 'Copyright {year}{author}',
    'BSD-3-Clause': 'Copyright {year}{author}',
    'BSD-3-Clause-Modification': 'Copyright {year}{author}',
    'LGPL-2.1-only': 'Copyright (C) {year}{author}',
    'LGPL-3.0-only': 'Copyright (C) {year}{author}',
    'MIT': 'Copyright (c) {year}{author}',
    'PSF': 'Copyright (c) {year}{author}',
    'CC0-1.0': '{author}. {package_name} is dedicated to the public domain under {license}.',
    'Unlicense': '{author}. {package_name} is dedicated to the public domain under {license}.',
}

# Files searched for COPYRIGHT_RE
COPYRIGHT_LOCATIONS_RE = re.compile(r'^(license.*|notice.*|copying.*|copyright.*|readme.*)$', re.I)

# General match for anything that looks like a copyright declaration
COPYRIGHT_RE = re.compile(
    r'^(?!i\.e\.,.*$)(Copyright\s+(?:©|\(c\)\s+)?(?:(?:[0-9 ,-]|present)+\s+)?(?:by\s+)?(.*))$', re.I
)

# Copyright strings to ignore, as they are not owners.  Most of these are from
# boilerplate license files.
#
# These match at the beginning of the copyright (the result of COPYRIGHT_RE).
COPYRIGHT_IGNORE_RE = [
    re.compile(r'copyright(:? and license)?$', re.I),
    re.compile(r'copyright (:?holder|owner|notice|license|statement|law|on the Program|and Related)', re.I),
    re.compile(r'Copyright & License -'),
    re.compile(r'copyright .yyyy. .name of copyright owner.', re.I),
    re.compile(r'copyright \(c\) <year>\s{2}<name of author>', re.I),
    re.compile(r'.*\sFree Software Foundation', re.I),
]

# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.base import ensure_unicode

from . import common


# Varnish < 4.x varnishadm output
def debug_health_mock(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "debug_health_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0


# Varnish >= 4.x && <= 5.x varnishadm output
def backend_list_mock_v4(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "backend_list_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0


# Varnish >= 5.x varnishadm output
def backend_list_mock_v5(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "backend_list_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output_json")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0


# Varnish >= 6.5 varnishadm output
def backend_list_mock_v6_5(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "backend_list_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output_json_6.5")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0


# Varnish >= 4.x && <= 5.x Varnishadm manually set backend to sick
def backend_manual_unhealthy_mock(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "backend_manually_unhealthy")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0

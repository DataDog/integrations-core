# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.checks.prometheus import GenericPrometheusCheck


class PrometheusCheck(GenericPrometheusCheck):
    AGNOSTIC_HTTP_CLIENT = True
    pass

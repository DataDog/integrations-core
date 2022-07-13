# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.sap_hana import SapHanaCheck


def test_default_tenant_databases(instance):
    check = SapHanaCheck('sap_hana', {}, [instance])
    assert check._schema == "SYS_DATABASES"


def test_override_tenant_databases(instance):
    instance["schema"] = "SYS"
    check = SapHanaCheck('sap_hana', {}, [instance])
    assert check._schema == "SYS"

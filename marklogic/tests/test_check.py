# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.marklogic import MarklogicCheck

from .common import INSTANCE


def test_submit_service_checks(aggregator):
    # type: (AggregatorStub) -> None
    check = MarklogicCheck('marklogic', {}, [INSTANCE])

    health_mocked_data = {
        'cluster-health-report': [
            {
                'resource-type': 'database',
                'resource-name': 'Last-Login',
                'code': 'HEALTH-DATABASE-NO-BACKUP',
                'message': 'Database has never been backed up.',
            },
            {'resource-type': 'database', 'resource-name': 'Fab', 'code': 'UNKNOWN'},
        ]
    }

    with mock.patch('datadog_checks.marklogic.api.MarkLogicApi.get_health', return_value=health_mocked_data):
        check.submit_service_checks()

        aggregator.assert_service_check(
            'marklogic.resource.health',
            MarklogicCheck.OK,
            tags=['foo:bar', 'resource:Last-Login'],
            message='HEALTH-DATABASE-NO-BACKUP: Database has never been backed up.',
        )
        aggregator.assert_service_check(
            'marklogic.resource.health',
            MarklogicCheck.UNKNOWN,
            tags=['foo:bar', 'resource:Fab'],
            message='UNKNOWN: No message.',
        )
        aggregator.assert_service_check('marklogic.can_connect', MarklogicCheck.OK)

        aggregator.assert_no_duplicate_service_checks()

# # (C) Datadog, Inc. 2018-present
# # All rights reserved
# # Licensed under Simplified BSD License (see LICENSE)
# import copy
# import time
#
# from datadog_checks.openstack_controller.retry import BackOffRetry
#
# from . import common
#
#
# def test_retry():
#     instance = copy.deepcopy(common.MOCK_CONFIG["instances"][0])
#     instance['tags'] = ['optional:tag1']
#     retry = BackOffRetry()
#     assert retry.should_run() is True
#     assert retry.backoff['retries'] == 0
#     # Make sure it is idempotent
#     assert retry.should_run() is True
#     assert retry.backoff['retries'] == 0
#
#     retry.do_backoff()
#     assert retry.should_run() is False
#     assert retry.backoff['retries'] == 1
#     scheduled_1 = retry.backoff['scheduled']
#     retry.do_backoff()
#     scheduled_2 = retry.backoff['scheduled']
#     retry.do_backoff()
#     scheduled_3 = retry.backoff['scheduled']
#     retry.do_backoff()
#     scheduled_4 = retry.backoff['scheduled']
#     assert retry.backoff['retries'] == 4
#     assert time.time() < scheduled_1 < scheduled_2 < scheduled_3 < scheduled_4

# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# project
from datadog_checks.teamcity import TeamCityCheck

# A path regularly used in the TeamCity Check
COMMON_PATH = "guestAuth/app/rest/builds/?locator=buildType:TestProject_TestBuild,sinceBuild:id:1,status:SUCCESS"

# These values are acceptable URLs
TEAMCITY_SERVER_VALUES = {

    # Regular URLs
    "localhost:8111/httpAuth": "http://localhost:8111/httpAuth",
    "localhost:8111/{}".format(COMMON_PATH): "http://localhost:8111/{}".format(COMMON_PATH),
    "http.com:8111/{}".format(COMMON_PATH): "http://http.com:8111/{}".format(COMMON_PATH),
    "http://localhost:8111/some_extra_url_with_http://": "http://localhost:8111/some_extra_url_with_http://",
    "https://localhost:8111/correct_url_https://": "https://localhost:8111/correct_url_https://",
    "https://localhost:8111/{}".format(COMMON_PATH): "https://localhost:8111/{}".format(COMMON_PATH),
    "http://http.com:8111/{}".format(COMMON_PATH): "http://http.com:8111/{}".format(COMMON_PATH),

    # <user>:<password>@teamcity.company.com
    "user:password@localhost:8111/http://_and_https://": "http://user:password@localhost:8111/http://_and_https://",
    "user:password@localhost:8111/{}".format(COMMON_PATH):
        "http://user:password@localhost:8111/{}".format(COMMON_PATH),
    "http://user:password@localhost:8111/{}".format(COMMON_PATH):
        "http://user:password@localhost:8111/{}".format(COMMON_PATH),
    "https://user:password@localhost:8111/{}".format(COMMON_PATH):
        "https://user:password@localhost:8111/{}".format(COMMON_PATH),
}


def test_server_normalization():
    """
    Make sure server URLs are being normalized correctly
    """

    teamcity = TeamCityCheck("teamcity", {}, {})

    for server, expected_server in TEAMCITY_SERVER_VALUES.iteritems():
        normalized_server = teamcity._normalize_server_url(server)

        assert expected_server == normalized_server

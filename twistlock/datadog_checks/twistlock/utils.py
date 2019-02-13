# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import requests
import logging

log = logging.getLogger(__file__)


def retrieve_json(config, path, warning):
    url = config.url + path
    auth = (config.username, config.password)
    response = requests.get(url, auth=auth, verify=config.ssl_verify)
    try:
        j = response.json()
        # it's possible to get a null response from the server
        # {} is a bit easier to deal with
        if not j:
            return {}
        return j
    except Exception as e:
        warning("cannot get stuff: {} response is: {}".format(e, response.text))
        raise e
        return {}

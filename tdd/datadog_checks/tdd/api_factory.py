from distutils.version import LooseVersion
from typing import Tuple

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from datadog_checks.tdd.api import Api
from datadog_checks.tdd.api_v5 import Apiv5


def make_api_client(check, instance) -> Tuple[Api, str]:
    options = {
        'host': instance.get('hosts', 'localhost:27017'),
        'serverSelectionTimeoutMS': instance.get('timeout', 5) * 1000,
    }
    mongo_client = MongoClient(**options)
    try:
        mongo_version = mongo_client.server_info().get('version', '0.0.0')
        check.log.debug('mongo_version: %s', mongo_version)
        if LooseVersion(mongo_version).version[0] == 5:
            return Apiv5(check, instance), None
        return None, f"Version {mongo_version} not supported"
    except ConnectionFailure as e:
        check.log.error('Exception: %s', e)
        return None, str(e)

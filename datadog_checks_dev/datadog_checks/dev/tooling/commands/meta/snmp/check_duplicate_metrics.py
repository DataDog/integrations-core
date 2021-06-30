from queue import Queue

import click
import yaml

from ..constants import get_root
from ..commands.console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success
from ...fs import file_exists

#from ....snmp.datadog_checks.snmp.utils import get_profile_definition


@click.command("check-duplicates", short_help="Check SNMP profiles for duplicate metrics", context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--file', help="Path to a profile file to validate")
# @click.option('-d', '--directory', help="Path to a directory of profiles to validate")
@click.option('-v', '--verbose', help="Increase verbosity of error messages", is_flag=True)

#imports?
# treat table and oid metrics separately?

#keep track of extends files - don't validate them twice

#open file
#extract extended profiles
# extract metrics
# compare for duplicates


#are the metrics i'm looking at correct?
# chain of validators



def check_duplicate_metrics(file, verbose):
    if not file_exists(file):
        echo_failure("File " + file + " not found, or could not be read")
        abort()

    profile = create_profile(file)


class Profile:
    def __init__(self):
        self.extends = []
        self.metrics = []
        self.path = ""
        self.has_duplicates = False
    def __repr__(self):
        return self.path


    def extract_extended_files(self, file):
        to_visit = Queue()
        self.seen = set()
        to_visit.put(file)
        while not to_visit.empty():
            file = to_visit.get()
            if file not in self.seen:
                config = get_file(file)
                try:
                    for extended_profile in config['extends']:
                        to_visit.put(extended_profile)
                except KeyError:
                    pass
                self.seen.add(file)
        self.extends = self.seen


def get_file(file):
    with open(file) as f:
        return yaml.safe_load(f)


def create_profile(file):
    profile = Profile()
    profile.path = file
    profile.extract_extended_files(file)
    config = get_file(file)
    profile.metrics = config['metrics']
    oids = extract_oids_from_table(profile.metrics)
    return profile



def extract_oids_from_metric(metrics_blob):
    oids_list = []
    for list_element in metrics_blob:
        oids_list.append(list_element['symbol']['OID'])
    return oids_list


def extract_oids_from_table(metrics_blob):
    oids_list = []
        for list_element in metrics_blob:
            for item in list_element:
                for el in item:
                    echo_info(el)









#check for oid, symbol, table keys  - snmp check folder - load profile


#_base.yaml [{'MIB': 'CPI-UNITY-MIB', 'symbol': {'OID': '1.3.6.1.4.1.30932.1.1.2.58.2.0', 'name': 'pduRole'}}, {'MIB': 'CPI-UNITY-MIB', 'symbol': {'OID': '1.3.6.1.4.1.30932.1.1.2.58.12.0', 'name': 'outOfService'}}]
{'_base.yaml', '_more.yaml'}

#more.yaml [{'MIB': 'JUNIPER-COS-MIB', 'table': {'OID': '1.3.6.1.4.1.2636.3.15.10', 'name': 'jnxCosIfsetQstatTable'}, 'forced_type': 'monotonic_count', 'symbols': [{'OID': '1.3.6.1.4.1.2636.3.15.10.1.3', 'name': 'jnxCosIfsetQstatQedPkts'}, {'OID': '1.3.6.1.4.1.2636.3.15.10.1.5', 'name': 'jnxCosIfsetQstatQedBytes'}, {'OID': '1.3.6.1.4.1.2636.3.15.10.1.7', 'name': 'jnxCosIfsetQstatTxedPkts'}]}]
{'_more.yaml'}

#_generic-if.yaml [{'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}, {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.1.0', 'name': 'panSessionUtilization'}}, {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.2.0', 'name': 'panSessionMax'}}, {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.3.0', 'name': 'panSessionActive'}}]
{'_generic-if.yaml'}




# >>> for el in generic:
# ...     print(el)
# ...
# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.1.0', 'name': 'panSessionUtilization'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.2.0', 'name': 'panSessionMax'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.3.0', 'name': 'panSessionActive'}}
# >>> for el in more:
# ...     print(el)
# ...
# {'MIB': 'JUNIPER-COS-MIB', 'table': {'OID': '1.3.6.1.4.1.2636.3.15.10', 'name': 'jnxCosIfsetQstatTable'}, 'forced_type': 'monotonic_count', 'symbols': [{'OID': '1.3.6.1.4.1.2636.3.15.10.1.3', 'name': 'jnxCosIfsetQstatQedPkts'}, {'OID': '1.3.6.1.4.1.2636.3.15.10.1.5', 'name': 'jnxCosIfsetQstatQedBytes'}, {'OID': '1.3.6.1.4.1.2636.3.15.10.1.7', 'name': 'jnxCosIfsetQstatTxedPkts'}]}
# >>> for el in base:
# ...     print(el)
# ...
# {'MIB': 'CPI-UNITY-MIB', 'symbol': {'OID': '1.3.6.1.4.1.30932.1.1.2.58.2.0', 'name': 'pduRole'}}
# {'MIB': 'CPI-UNITY-MIB', 'symbol': {'OID': '1.3.6.1.4.1.30932.1.1.2.58.12.0', 'name': 'outOfService'}}



# collections.counter on OIDs? - use strings to compare OIDs








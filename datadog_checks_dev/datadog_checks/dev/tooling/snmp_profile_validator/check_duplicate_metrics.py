from collections import Counter

import click
import yaml

from ..constants import get_root
from ..commands.console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

#from ....snmp.datadog_checks.snmp.utils import get_profile_definition - can I do this?


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


def check_duplicate_metrics(file, verbose):
    m = create_profile(file)
    extract_extended_profiles(m)


class Profile:
    def __init__(self):
        self.extends = [] #paths to files in extends section
        self.metrics = [] # metrics defined
        self.path = ""
        self.has_duplicates = False
    def __repr__(self):
        return self.path

def get_file(file):
      with open(file) as f:
        return yaml.safe_load(f)
# {'extends': ['_base.yaml', '_generic-if.yaml'], 'metrics': [{'MIB': 'HOST-RESOURCES-MIB', 'table': {'name': 'hrSWRunPerfTable', 'OID': '1.3.6.1.2.1.25.5.1'}, 'symbols': [{'name': 'hrSWRunPerfMem', 'OID': '1.3.6.1.2.1.25.5.1.1.2'}, {'name': 'hrSWRunPerfCPU', 'OID': '1.3.6.1.2.1.25.5.1.1.1'}], 'metric_tags': [{'column': {'name': 'hrSWRunIndex', 'OID': '1.3.6.1.2.1.25.4.2.1.1'}, 'table': 'hrSWRunTable', 'tag': 'run_index'}]}]}

def create_profile(file):
    profile = Profile()
    profile.path = file
    config = get_file(file)
    profile.extends = config['extends']
    profile.metrics = config['metrics']
    return profile


def extract_extended_profiles(profile):
    for filename in profile.extends:
        config = get_file(filename)
        profile.metrics = profile.metrics + config['metrics']
    return profile

# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'CISCO-ENTITY-SENSOR-MIB', 'table': {'OID': '1.3.6.1.4.1.9.9.91.1.1.1', 'name': 'entSensorValueTable'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.1.0', 'name': 'panSessionUtilization'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.2.0', 'name': 'panSessionMax'}}
# {'MIB': 'PAN-COMMON-MIB', 'symbol': {'OID': '1.3.6.1.4.1.25461.2.1.2.3.3.0', 'name': 'panSessionActive'}}




def find_duplicates(profile):
# metrics need to be associated with their filenames
# Counter like object that can keep the metric-filename link




#collections.Counter(a).items() if count > 1]

def report_duplicates(profile):
    # duplicate metric oid and files it is defined in, line no?
    pass







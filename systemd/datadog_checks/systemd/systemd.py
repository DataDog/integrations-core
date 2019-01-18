# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pystemd
from pystemd.systemd1 import Manager
from pystemd.systemd1 import Unit

from datetime import datetime

from datadog_checks.base import AgentCheck


class SystemdCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(SystemdCheck, self).__init__(name, init_config, agentConfig, instances)

        # to store the state of a unit and compare it at the next run
        self.unit_cache = {}

        # Ex: unit_cache = {
        #   <unit_id>: {
        #       'unit_state': state,
        #       'changes_since': <ISO8601 date time>
        #   }
        # }

    def check(self, instance):
        units = instance.get('units', [])
        collect_all = instance.get('collect_all_units')

        if units:
            for unit_id in units:
                self.get_unit_state(unit_id)
        if collect_all == True:
            # we display status for all units if no unit has been specified in the configuration file
            self.log.warn("Getting status for all units. Performance might be impacted!")
            self.get_active_inactive_units()

    def get_all_listed_units(self, unit_name):
        cached_units = self.unit_cache.get(unit_name, {}).get('unit_state')
        changes_since = datetime.utcnow().isoformat()
        if cached_units is None:
            units = self.get_all_units()
        else:
            previous_changes_since = self.unit_state_cache.get(unit_name, {}).get('changes_since')
            updated_units = self.update_unit_state(cached_units, previous_changes_since)

        # Initialize or update cache for this instance
        self.unit_state_cache[unit_name] = {
            'unit_state': unit_state,
            'changes_since': changes_since
        }
    
    def update_unit_state(self, cached_units, changes_since):
        # TODO

    def get_active_inactive_units(self):
        # returns the number of active and inactive units
        manager = Manager()
        manager.load()
        list_units = manager.Manager.ListUnitFiles()

        # remove units that have an @ symbol in their names - cannot seem to get unit info then - to investigate
        unit_names = [unit[0] for unit in list_units if '@' not in unit[0]]

        active_units = inactive_units = 0

        for unit in unit_names:
        # full unit name includes path e.g. /lib/systemd/system/networking.service - we take the string before the last "/"
            unit_short_name = unit.rpartition('/')[2]
            # self.log.info(unit_short_name)
            try:   
                unit_loaded = Unit(unit_short_name, _autoload=True)
                unit_state = unit_loaded.Unit.ActiveState
                if unit_state == b'active':
                    active_units += 1
                if unit_state == b'inactive':
                    inactive_units += 1
            except pystemd.dbusexc.DBusInvalidArgsError as e:
                self.log.debug("Cannot retrieve unit status for {}".format(unit_short_name))
        
        self.gauge('systemd.units.active', active_units)
        self.gauge('systemd.units.inactive', inactive_units)
        
    def get_unit_state(self, unit_name):
        try:
            unit = Unit(unit_name, _autoload=True)
            # self.log.info(str(unit_name))
            tag = unit_name.split('.', 1)[0]
            self.log.info(tag)
            state = unit.Unit.ActiveState
            # Send a service check: OK if the unit is active, CRITICAL if inactive
            if state == b'active':
                self.service_check(
                    AgentCheck.OK,
                    tags=["unit:{}".format(unit_name)]
                )
            if state == b'inactive':
                self.service_check(
                    AgentCheck.CRITICAL,
                    tags=["unit:{}".format(unit_name)]
                )
            if unit_id in unit_cache:
                previous_status = unit_cache[unit_id]['state']
                if previous_status != active_status:
                    self.event(...)
                unit_cache[unit_id]['state'] = active_status
            else:
                unit_cache[unit_id]['state'] = active_status

        except pystemd.dbusexc.DBusInvalidArgsError as e:
            self.log.info("Unit name invalid for {}".format(unit_name))

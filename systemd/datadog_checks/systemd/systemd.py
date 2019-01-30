# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict
import pystemd
from pystemd.systemd1 import Manager
from pystemd.systemd1 import Unit

from datetime import datetime

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative


class SystemdCheck(AgentCheck):

    UNIT_STATUS_SC = 'systemd.unit.active'

    def __init__(self, name, init_config, agentConfig, instances=None):
        if instances is not None and len(instances) > 1:
            raise ConfigurationError('Systemd check only supports one configured instance.')
        super(SystemdCheck, self).__init__(name, init_config, agentConfig, instances)

        instance = instances[0]
        self.collect_all = is_affirmative(instance.get('collect_all_units', False))
        self.units = instance.get('units', [])
        # to store the state of a unit and compare it at the next run
        self.unit_cache = defaultdict(dict)

        # unit_cache = {
        #    "units": {
        #        "networking.service": "active",
        #        "cron.service": "inactive",
        #        "ssh.service": "active"
        #    },
        #    "change_since": "iso_time"
        #}

        self.units_in_dict = None
        
    def check(self, instance):
        
        if self.units:
            # self.log.info(units)
            for unit in self.units:
                self.get_unit_state(unit)
        if self.collect_all == True:
            # we display status for all units if no unit has been specified in the configuration file
            self.get_active_inactive_units()

        self.units_in_dict = 'units'
        
        self.get_all_units(self.units)


    def get_all_units(self, instance):
        cached_units = self.unit_cache.get(self.units_in_dict)
        changes_since = datetime.utcnow().isoformat()
        if cached_units is None:
            updated_units = self.get_listed_units()
        else:
            previous_changes_since = self.unit_cache.get(self.units_in_dict, {}).get('changes_since')
            updated_units = self.update_unit_cache(cached_units, previous_changes_since)
            self.log.info(updated_units)

        # Initialize or update cache for this instance
        self.unit_cache[self.units_in_dict] = updated_units
        self.unit_cache['change_since'] = changes_since
    
    def get_listed_units(self):
        manager = Manager()
        manager.load()

        units = self.units

        return {unit: self.get_state_single_unit(unit) for unit in units}

    def update_unit_cache(self, cached_units, changes_since):

        updated_units = self.get_listed_units()

        returned_cache = {}

        returned_cache[self.units_in_dict] = updated_units
        returned_cache['changes_since'] = changes_since

        return returned_cache  # a new cache, dict of units and timestamp

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

    def get_state_single_unit(self, unit_id):
        try:
            unit = Unit(unit_id, _autoload=True)
            # self.log.info(str(unit_name))
            state = unit.Unit.ActiveState
            return state
        except pystemd.dbusexc.DBusInvalidArgsError as e:
            self.log.info("Unit name invalid for {}".format(unit_id))
        
    def get_unit_state(self, unit_id):
        try:
            unit = Unit(unit_id, _autoload=True)
            # self.log.info(str(unit_name))
            state = unit.Unit.ActiveState
            # Send a service check: OK if the unit is active, CRITICAL if inactive
            if state == b'active':
                self.service_check(
                    self.UNIT_STATUS_SC,
                    AgentCheck.OK,
                    tags=["unit:{}".format(unit_id)]
                )
            elif state == b'inactive':
                self.service_check(
                    self.UNIT_STATUS_SC,
                    AgentCheck.CRITICAL,
                    tags=["unit:{}".format(unit_id)]
                )
                
            if unit_id in self.unit_cache.get('units', {}):
                previous_status = self.unit_cache[self.units_in_dict][unit_id]
                if previous_status != state:
                    # TODO:
                    # self.event(...)
                    self.unit_cache[self.units_in_dict][unit_id] = state
            else:
                self.unit_cache[self.units_in_dict][unit_id] = state

        except pystemd.dbusexc.DBusInvalidArgsError as e:
            self.log.info("Unit name invalid for {}".format(unit_id))

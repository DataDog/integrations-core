# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pystemd
from pystemd.systemd1 import Manager
from pystemd.systemd1 import Unit

from datadog_checks.base import AgentCheck


class SystemdCheck(AgentCheck):
    def check(self, instance):
        units = instance.get('units', [])
        # self.log.info(units[1])
        # self.log.info(units)

        if units:
            # self.get_unit_state(units)
            for u in units:
                self.get_unit_state([u][unit_id])
        
        self.get_active_inactive_units()

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
                # self.log.info(unit_state)
            except pystemd.dbusexc.DBusInvalidArgsError as e:
                self.log.debug("Cannot retrieve unit status for {}".format(unit_short_name))
        
        self.gauge('systemd.units.active', active_units)
        self.gauge('systemd.units.inactive', inactive_units)
        
    def get_unit_state(self, unit_name):
        try: 
            unit = Unit(unit_name, _autoload=True)
            state = unit.Unit.ActiveState
            # 1 if active, 0 if inactive
            if state == b'active':
                active_status = 1
            if state == b'inactive':
                active_status = 0
            self.gauge('systemd.unit.active', active_status, tags=unit_name)
        except pystemd.dbusexc.DBusInvalidArgsError as e:
            self.log.info("Unit name invalid for {}".format(unit_name))

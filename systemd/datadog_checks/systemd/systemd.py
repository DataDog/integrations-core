# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict
import pystemd
from pystemd.systemd1 import Manager
from pystemd.systemd1 import Unit

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.utils.subprocess_output import (
    get_subprocess_output,
    SubprocessOutputEmptyError,
)


class SystemdCheck(AgentCheck):

    UNIT_STATUS_SC = 'systemd.unit.active'

    def __init__(self, name, init_config, instances):
        if instances is not None and len(instances) > 1:
            raise ConfigurationError('Systemd check only supports one configured instance.')
        super(SystemdCheck, self).__init__(name, init_config, instances)

        instance = instances[0]
        self.collect_all = is_affirmative(instance.get('collect_all_units', False))
        self.units = instance.get('units', [])
        # to store the state of a unit and compare it at the next run
        self.unit_cache = defaultdict(dict)

        # unit_cache = {
        #    "units": {
        #        "<unit_name>": "<unit_status>",
        #        "cron.service": "inactive",
        #        "ssh.service": "active"
        #    }
        # }

    def check(self, instance):
        if self.units:
            for unit in self.units:
                self.get_unit_state(unit)
                self.get_number_processes(unit)
        if self.collect_all:
            # we display status for all units if no unit has been specified in the configuration file
            self.get_active_inactive_units()

        self.get_all_units(self.units)

    def get_all_units(self, cached_units):
        if not cached_units:
            cached_units = self.unit_cache.get('units')

        updated_units = self.get_listed_units()

        # Initialize or update cache for this instance
        self.unit_cache = {
            'units': updated_units
        }

        return self.unit_cache, cached_units

    def get_listed_units(self):
        manager = Manager()
        manager.load()
        units = self.units

        return {unit: self.get_state_single_unit(unit) for unit in units}

    def update_unit_cache(self):
        returned_cache = {}
        returned_cache = self.get_listed_units()

        return returned_cache

    def get_active_inactive_units(self):
        # returns the number of active and inactive units
        manager = Manager()
        manager.load()
        list_units = manager.Manager.ListUnitFiles()

        unit_names = [unit[0] for unit in list_units]

        active_units = inactive_units = 0

        for unit in unit_names:
            # full unit name includes path - we take the string before the last "/"
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
                self.log.debug("Cannot retrieve unit status for {}".format(unit_short_name), e)

        self.gauge('systemd.units.active', active_units)
        self.gauge('systemd.units.inactive', inactive_units)

    def get_state_single_unit(self, unit_id):
        try:
            unit = Unit(unit_id, _autoload=True)
            state = unit.Unit.ActiveState
            return state
        except pystemd.dbusexc.DBusInvalidArgsError as e:
            self.log.info("Unit name invalid for {}".format(unit_id), e)

    def get_unit_state(self, unit_id):
        try:
            unit = Unit(unit_id, _autoload=True)
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
                previous_status = self.unit_cache['units'][unit_id]
                if previous_status != state:
                    self.event({
                        "event_type": "unit.status.changed",
                        "msg_title": "unit {} changed state".format(unit_id),
                        "msg_text": "it is now: {}".format(state),
                        "tags": ["unit:status_changed"]
                    })
                    self.unit_cache['units'][unit_id] = state

            else:
                self.unit_cache['units'][unit_id] = state

        except pystemd.dbusexc.DBusInvalidArgsError as e:
            self.log.info("Unit name invalid for {}".format(unit_id), e)

    def get_number_processes(self, unit_id):
        systemctl_flags = ['status', unit_id]
        try:
            output = get_subprocess_output(["systemctl"] + systemctl_flags, self.log)
            output_to_parse = output[0].split()
            number_of_pids = output_to_parse.count(u'Process:')
            self.gauge('systemd.unit.processes', number_of_pids, tags=["unit:{}".format(unit_id)])
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting systemctl stats.")

# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

from collections import defaultdict
from six import iteritems

import pystemd
from pystemd.systemd1 import Unit

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base import ensure_unicode


class SystemdCheck(AgentCheck):

    UNIT_STATUS_SC = 'systemd.unit.active'

    def __init__(self, name, init_config, instances):
        if instances is not None and len(instances) > 1:
            raise ConfigurationError('Systemd check only supports one configured instance.')
        super(SystemdCheck, self).__init__(name, init_config, instances)

        instance = instances[0]
        self.units_watched = instance.get('units', [])
        self.tags = instance.get('tags', [])
        # report state of all systemd units found
        self.report_status = instance.get('report_status', False)

        # cache to store unit states and compare them at the next check run
        # unit_cache = {
        #   "<unit_name>": "<unit_status>",
        #   "cron.service": "inactive",
        #   "ssh.service": "active"
        # }
        self.unit_cache = defaultdict(dict)

    def check(self, instance):
        current_unit_status = defaultdict(dict)
        for u in self.units_watched:
            current_unit_status[u] = self.get_state_single_unit(u)
        # initialize the cache if it's empty
        if not self.unit_cache:
            self.unit_cache = current_unit_status

        for unit in self.units_watched:
            self.send_service_checks(unit, self.get_state_single_unit(unit), self.tags)

        # find out which units have changed state, units that can no longer be found or units found
        changed_units, created_units, deleted_units = self.list_status_change(current_unit_status)

        self.report_changed_units(changed_units, self.tags)
        self.report_deleted_units(deleted_units, self.tags)
        self.report_created_units(created_units, self.tags)

        if self.report_status:
            all_units = self.get_all_unit_status()
            self.report_statuses(all_units, self.tags)

        # we update the cache at the end of the check run
        self.unit_cache = current_unit_status

    def get_all_unit_status(self):
        m = pystemd.systemd1.Manager(_autoload=True)
        # list_unit_files is a list of tuples including the unit names/ids and status
        list_unit_files = m.Manager.ListUnits()

        unit_status = defaultdict(dict)

        for unit in list_unit_files:
            unit_short_name = unit[0]  # unit name/id
            unit_state = unit[3]  # unit state
            unit_status[unit_short_name] = unit_state

        return unit_status

    def list_status_change(self, current_unit_status):
        # returns a tuple of dicts for unit changes
        changed = defaultdict(dict)
        deleted = defaultdict(dict)
        created = copy.deepcopy(current_unit_status)

        for unit_short_name, previous_unit_status in iteritems(self.unit_cache):
            # We remove all previous cached entries from the current unit status
            created.pop(unit_short_name, None)
            # We check status changes between the previous cached unit status and the current unit status
            current_status = current_unit_status.get(unit_short_name)
            if current_status:
                if current_status != previous_unit_status:
                    self.log.debug("unit {} changed state, it is now {}".format(unit_short_name, current_status))
                    changed[unit_short_name] = current_status
            else:
                self.log.debug("unit {} not found".format(unit_short_name))
                # We list all previous cached unit status that do not exist anymore
                deleted[unit_short_name] = previous_unit_status

        return changed, created, deleted

    def report_changed_units(self, units, tags):
        for unit, state in iteritems(units):
            self.event({
                "event_type": "unit.status.changed",
                "msg_title": "unit {} changed state".format(unit),
                "msg_text": "it is now: {}".format(state),
                "tags": tags
            })

    def report_deleted_units(self, units, tags):
        for unit, state in iteritems(units):
            self.event({
                "event_type": "unit.status.deleted",
                "msg_title": "unit {} cannot be found".format(unit),  # TODO: check wording
                "msg_text": "last reported status was: {}".format(state),
                "tags": tags
            })

    def report_created_units(self, units, tags):
        for unit, state in iteritems(units):
            self.event({
                "event_type": "unit.status.created",
                "msg_title": "new unit {} has been found".format(unit),  # TODO: check wording
                "msg_text": "status is: {}".format(state),
                "tags": tags
            })

    def report_statuses(self, units, tags):
        active_units = inactive_units = 0
        for unit, state in iteritems(units):
            state = ensure_unicode(state)
            try:
                if state == 'active':
                    active_units += 1
                if state == 'inactive':
                    inactive_units += 1
            except pystemd.dbusexc.DBusInvalidArgsError as e:
                self.log.debug("Cannot retrieve unit status for {}, {}".format(unit, e))

        self.gauge('systemd.units.active', active_units, tags)
        self.gauge('systemd.units.inactive', inactive_units, tags)

    def get_state_single_unit(self, unit_id):
        try:
            unit = Unit(unit_id, _autoload=True)
            state = unit.Unit.ActiveState
            return state
        except pystemd.dbusexc.DBusInvalidArgsError as e:
            self.log.info("Unit name invalid for {}, {}".format(unit_id, e))

    def send_service_checks(self, unit_id, state, tags):
        state = ensure_unicode(state)
        if state == 'active' or 'activating':
            self.service_check(
                self.UNIT_STATUS_SC,
                AgentCheck.OK,
                tags=["unit:{}".format(unit_id)] + tags
            )
        elif state == 'inactive' or state == 'failed':
            self.service_check(
                self.UNIT_STATUS_SC,
                AgentCheck.CRITICAL,
                tags=["unit:{}".format(unit_id)] + tags
            )
        elif state == 'deactivating':
            self.service_check(
                self.UNIT_STATUS_SC,
                AgentCheck.WARN,
                tags=["unit:{}".format(unit_id)] + tags
            )
        else:
            self.service_check(
                self.UNIT_STATUS_SC,
                AgentCheck.CRITICAL,
                tags=["unit:{}".format(unit_id)] + tags
            )

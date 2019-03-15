# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

from collections import defaultdict
from six import iteritems
import pystemd
from pystemd.systemd1 import Manager
from pystemd.systemd1 import Unit

from datadog_checks.base import AgentCheck, ConfigurationError
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
        self.units_watched = instance.get('units', [])
        self.tags = instance.get('tags', [])
        self.report_status = instance.get('report_status', False)
        self.report_processes = instance.get('report_processes', True)

        # self.collect_all = is_affirmative(instance.get('collect_all_units', False))
        # self.units = instance.get('units', [])
        # to store the state of a unit and compare it at the next run
        self.unit_cache = defaultdict(dict)

        # unit_cache = {
        #   "<unit_name>": "<unit_status>",
        #   "cron.service": "inactive",
        #   "ssh.service": "active"
        # }

    def check(self, instance):
        # units_watched = instance.get('units', [])
        # populate unit cache
        # current_unit_status = self.get_all_unit_status()
        current_unit_status = defaultdict(dict)
        for u in self.units_watched:
            current_unit_status[u] = self.get_state_single_unit(u)
        # initialize the cache if it's empty
        if not self.unit_cache:
            self.unit_cache = current_unit_status

        for unit in self.units_watched:
            if self.report_processes:
                self.report_number_processes(unit, self.tags)
            self.send_service_checks(unit, self.get_state_single_unit(unit), self.tags)

        changed_units, created_units, deleted_units = self.list_status_change(current_unit_status)

        self.report_changed_units(changed_units, self.tags)
        self.report_deleted_units(deleted_units, self.tags)
        self.report_created_units(created_units, self.tags)

        if self.report_status:
            self.report_statuses(current_unit_status, self.tags, self.report_processes)

        # we update the cache at the end of the check run
        self.unit_cache = current_unit_status

    def get_all_unit_status(self):
        m = pystemd.systemd1.Manager(_autoload=True)
        list_unit_files = m.Manager.ListUnits()
        manager = Manager()
        manager.load()

        # list_unit_files = manager.Manager.ListUnitFiles()

        unit_status = defaultdict(dict)

        for unit in list_unit_files:
            # full unit name includes path - we take the string before the last "/"
            unit_short_name = unit[0]
            # unit_short_name = u.rpartition('/')[2]
            unit_state = unit[3]
            # unit_state = self.get_state_single_unit(unit_short_name)
            unit_status[unit_short_name] = unit_state

        return unit_status

    def list_status_change(self, current_unit_status):
        changed = defaultdict(dict)
        deleted = defaultdict(dict)
        created = copy.deepcopy(current_unit_status)

        for unit_short_name, previous_unit_status in iteritems(self.unit_cache):
            # We remove all previous cached entries from the current unit status
            created.pop(unit_short_name, None)
            # del created[unit_short_name]
            # We check status changes between the previous cached unit status and the current unit status
            current_status = current_unit_status.get(unit_short_name)
            if current_status:
                if current_status != previous_unit_status:
                    changed[unit_short_name] = current_status
                    self.log.info("current status IS found")
            else:
                self.log.info("current unit not found")
                # We list all previous cached unit status that do not exist anymore
                deleted[unit_short_name] = previous_unit_status

        return changed, created, deleted

    def report_changed_units(self, units, tags):
        for unit, state in iteritems(units):
            # self.log.info("changed units:")
            # self.log.info(units)
            self.event({
                "event_type": "unit.status.changed",
                "msg_title": "unit {} changed state".format(unit),
                "msg_text": "it is now: {}".format(state),
                "tags": tags
            })

    def report_deleted_units(self, units, tags):
        for unit, state in iteritems(units):
            # self.log.info("deleted units:")
            # self.log.info(units)
            self.event({
                "event_type": "unit.status.deleted",
                "msg_title": "unit {} cannot be found".format(unit),  # TODO: check wording
                "msg_text": "last reported status was: {}".format(state),
                "tags": tags
            })

    def report_created_units(self, units, tags):
        for unit, state in iteritems(units):
            # self.log.info("created units:")
            # self.log.info(units)
            self.event({
                "event_type": "unit.status.created",
                "msg_title": "new unit {} has been found".format(unit),  # TODO: check wording
                "msg_text": "status is: {}".format(state),
                "tags": tags
            })

    def report_statuses(self, units, tags, report_processes):
        active_units = inactive_units = 0
        for unit, state in iteritems(units):
            # self.log.info("state_debug:{}".format(state))
            try:
                if state == b'active':
                    active_units += 1
                    """
                    self.service_check(
                        self.UNIT_STATUS_SC,
                        AgentCheck.OK,
                        tags=["unit:{}".format(unit)] + tags
                    )
                    """
                    # if report_processes:
                    #    self.report_number_processes(unit, tags)
                    # active_units += 1
                if state == b'inactive':
                    inactive_units += 1
                    """
                    self.service_check(
                        self.UNIT_STATUS_SC,
                        AgentCheck.CRITICAL,
                        tags=["unit:{}".format(unit)] + tags
                    )
                    """
                    # inactive_units += 1
            except pystemd.dbusexc.DBusInvalidArgsError as e:
                self.log.debug("Cannot retrieve unit status for {}, {}".format(unit, e))

        self.gauge('systemd.units.active', active_units)
        self.gauge('systemd.units.inactive', inactive_units)

    def get_state_single_unit(self, unit_id):
        try:
            unit = Unit(unit_id, _autoload=True)
            state = unit.Unit.ActiveState
            return state
        except pystemd.dbusexc.DBusInvalidArgsError as e:
            self.log.info("Unit name invalid for {}, {}".format(unit_id, e))

    def send_service_checks(self, unit_id, state, tags):
        if state == b'active' or b'activating':
            self.service_check(
                self.UNIT_STATUS_SC,
                AgentCheck.OK,
                tags=["unit:{}".format(unit_id)] + tags
            )
        elif state == b'inactive' or state == b'failed':
            self.service_check(
                self.UNIT_STATUS_SC,
                AgentCheck.CRITICAL,
                tags=["unit:{}".format(unit_id)] + tags
            )
        elif state == b'deactivating':
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

    def report_number_processes(self, unit, tags):
        systemctl_flags = ['status', unit]
        try:
            output = get_subprocess_output(["systemctl"] + systemctl_flags, self.log)
            output_to_parse = output[0].split()
            number_of_pids = output_to_parse.count(u'Process:')
            self.gauge('systemd.unit.processes', number_of_pids, tags=["unit:{}".format(unit)] + tags)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting systemctl stats.")

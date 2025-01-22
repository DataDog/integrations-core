# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import subprocess
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck

from .constants import SHOW_METRIC_DATA, UNIT_PATTERN

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 7222
TO_BYTES = {'b': 1, 'kb': 1e3, 'mb': 1e6, 'gb': 1e9, 'tb': 1e12}
CONNECTION_STRING = 'tcp://{}:{}'


class TibcoEMSCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'tibco_ems'

    def __init__(self, name, init_config, instances):
        super(TibcoEMSCheck, self).__init__(name, init_config, instances)
        # Allow to specify a complete command for tibemsadmin such as `docker exec <container> tibemsadmin`
        default_tibemsadmin_cmd = init_config.get('tibemsadmin', '/usr/bin/tibemsadmin')
        tibemsadmin_cmd = self.instance.get('tibemsadmin', default_tibemsadmin_cmd).split()
        host = self.instance.get('host', DEFAULT_HOST)
        port = self.instance.get('port', DEFAULT_PORT)
        username = self.instance.get('username')
        password = self.instance.get('password')
        script_path = self.instance.get('script_path')
        server_string = CONNECTION_STRING.format(host, port)
        self.tags = self.instance.get('tags', [])
        self.parsed_data = {}

        self.cmd = tibemsadmin_cmd + [
            '-server',
            server_string,
            '-user',
            username,
            '-password',
            password,
            '-script',
            script_path,
        ]

    def check(self, _):

        output = self.run_tibco_command()
        decoded_output = output.decode('utf-8')

        # Sanitize the output
        cleaned_data = decoded_output.replace('\r', '').strip()

        # Split the output into command sections
        sections = self._section_output(cleaned_data)

        # Parse the output
        for command, section in sections.items():
            pattern = SHOW_METRIC_DATA[command]['regex']
            if command == 'show server':
                self.parsed_data[command] = self._parse_show_server(section, pattern)
            else:
                try:
                    self.parsed_data[command] = self._parse_factory(section, pattern)
                except Exception as e:
                    self.log.error('Error parsing command %s: %s', command, e)
                    continue

        for command, metric_info in self.parsed_data.items():
            metric_keys = SHOW_METRIC_DATA[command]['metric_keys']
            tag_keys = SHOW_METRIC_DATA[command]['tags']
            metric_prefix = SHOW_METRIC_DATA[command]['metric_prefix']

            if command == 'show server':
                self._submit_metrics_factory(metric_prefix, metric_info, metric_keys, tag_keys)
            else:
                for metric_entry in metric_info:
                    self._submit_metrics_factory(metric_prefix, metric_entry, metric_keys, tag_keys)

    def run_tibco_command(self):
        try:
            output = subprocess.run(self.cmd, capture_output=True).stdout
        except subprocess.CalledProcessError as e:
            self.log.error('Error running command: %s', e)
            return

        return output

    def _parse_unit(self, value):
        match = UNIT_PATTERN.match(value)
        if match:
            return {'value': float(match.group('value')), 'unit': match.group('unit')}
        return value

    def _parse_generic(self, value):
        try:
            return int(value)
        except ValueError:
            return value

    def _parse_show_server(self, output, pattern):
        server_data = {}
        lines = output.strip().split('\n')

        rate_pattern = re.compile(r'(?P<value>\d+)\s*(?P<unit>\S+)')

        def parse_value(key, value):
            if key == 'server':
                version_match = re.search(r'\d+\.\d+\.\d+', value)
                if version_match:
                    server_data['version'] = version_match.group()
                server_data[key] = value
            elif key in ['topics', 'queues', 'client_connections']:
                server_data[key] = int(value.split(' ')[0])
            elif "rate" in key:
                parse_rate(server_data, key, value)
            elif key == 'uptime':
                server_data[key] = parse_server_uptime(value)
            elif any(metric in key for metric in metrics_with_units):
                server_data[key] = self._parse_unit(value)
            else:
                server_data[key] = self._parse_generic(value)

        def parse_rate(server_data, metric_key, value):
            rates = value.split(',')
            count_match = rate_pattern.match(rates[0].strip())
            unit_match = UNIT_PATTERN.match(rates[1].strip())
            if count_match and unit_match:
                server_data[f"{key}"] = float(count_match.group('value'))
                server_data[f"{key}_size"] = {}
                server_data[f"{key}_size"]['value'] = float(unit_match.group('value'))
                server_data[f"{key}_size"]['unit'] = unit_match.group('unit')
            return server_data

        def parse_server_uptime(uptime_str):
            # Regex to extract days, hours, minutes, and seconds
            uptime_pattern = re.compile(
                r'(?:(?P<days>\d+)\s+days\s*)?(?:(?P<hours>\d+)\s+hours\s*)?(?:(?P<minutes>\d+)\s+minutes\s*)?(?:(?P<seconds>\d+)\s+seconds\s*)?'
            )
            match = uptime_pattern.match(uptime_str)
            if not match:
                return 0

            days = int(match.group('days') or 0) * 86400
            hours = int(match.group('hours') or 0) * 3600
            minutes = int(match.group('minutes') or 0) * 60
            seconds = int(match.group('seconds') or 0)

            total_seconds = days + hours + minutes + seconds
            return total_seconds

        metrics_with_units = [
            'pending_message_size',
            'message_memory_usage',
            'message_memory_pooled',
            'synchronous_storage',
            'asynchronous_storage',
            'inbound_message_rate_size',
            'outbound_message_rate_size',
            'storage_read_rate_size',
            'storage_write_rate_size',
        ]

        for line in lines:
            match = pattern.match(line)
            if match:
                key = match.group('key').strip().lower().replace(' ', '_')
                value = match.group('value').strip()
                parse_value(key, value)

        return server_data

    def _parse_factory(self, output, pattern):
        data = []
        lines = output.strip().split('\n')

        metrics_with_units = [
            'pending_messages_size',
            'pending_persistent_messages_size',
            'total_messages_size',
            'uncommitted_transactions_size',
            'messages_rate_size',
        ]

        def sanitize_name(name):
            '''
            Sanitize the metric values to get rid of special characters
            except for underscores and dots.
            '''
            return re.sub(r'[^\w\._]', '', name)

        for line in lines[1:]:
            match = pattern.match(line)
            if match:
                info = match.groupdict()
                if info.get('queue_name') == '>' or info.get('topic_name') == '>':
                    continue
                for key, value in info.items():
                    if key in metrics_with_units:
                        info[key] = self._parse_unit(value)
                    else:
                        value = sanitize_name(value)
                        info[key] = self._parse_generic(value)
                data.append(info)
        return data

    def _submit_metrics_factory(self, prefix, metric_data, metric_names, tag_keys):

        tags = []
        for key in tag_keys:
            if prefix == 'server':
                # Add server tags to all metrics
                self.tags.append(f"server_{key}:{metric_data[key]}")
            else:
                if metric_data.get(key):
                    tags.append(f"{key}:{metric_data[key]}")

        tags.extend(self.tags)
        for metric_name in metric_names:
            metric_info = metric_data[metric_name]
            if metric_name in metric_data:
                if isinstance(metric_info, dict):
                    self.gauge(
                        f"{prefix}.{metric_name}",
                        (metric_info['value'] * TO_BYTES[metric_info['unit'].lower()]),
                        tags=tags,
                    )
                else:
                    self.gauge(f"{prefix}.{metric_name}", metric_info, tags=tags)

    def _section_output(self, output):
        '''
        Split the output into sections based on the command
        '''
        sections = {}
        current_command = None
        current_section = []

        for line in output.strip().split('\n'):
            if line.startswith("Command:"):
                if current_command:
                    sections[current_command] = "\n".join(current_section)
                current_command = line.split("Command:")[1].strip()
                current_section = []
            elif current_command:
                current_section.append(line)

        if current_command:
            sections[current_command] = "\n".join(current_section)

        return sections

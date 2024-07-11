# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.subprocess_output import get_subprocess_output

from .constants import SHOW_METRIC_DATA, unit_pattern

TO_BYTES = {'B': 1, 'Kb': 1e3, 'Mb': 1e6, 'Gb': 1e9, 'Tb': 1e12}


class TibcoEMSCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'tibco_ems'

    def __init__(self, name, init_config, instances):
        super(TibcoEMSCheck, self).__init__(name, init_config, instances)
        # Allow to specify a complete command for tibemsadmin such as `docker exec <container> tibemsadmin`
        # default_tibemsadmin_cmd = init_config.get('tibemsadmin', 'tibemsadmin')
        default_tibemsadmin_cmd = init_config.get('tibemsadmin', 'docker container exec tibco tibemsadmin')
        tibemsadmin_cmd = self.instance.get('tibemsadmin', default_tibemsadmin_cmd).split()
        host = self.instance.get('host', 'localhost')
        port = self.instance.get('port', 7222)
        username = self.instance.get('username', 'admin')
        password = self.instance.get('password', 'admin')
        script_path = self.instance.get('script_path', '/opt/tibco/ems/10.1/show_stats')
        self.tags = self.instance.get("tags", [])
        self.parsed_data = {}

        # Build the tibeamsadmin command
        self.cmd = tibemsadmin_cmd + [
            '-server',
            f'tcp://{host}:{port}',
            '-user',
            username,
            '-password',
            password,
            '-script',
            script_path,
        ]

    def check(self, _):

        # Run the command
        output, err, code = get_subprocess_output(self.cmd, self.log)
        if err or 'Error:' in output or code != 0:
            self.log.error('Error running command: %s', err)
            return

        # Sanitize the output
        cleaned_data = output.replace('\r', '').strip()

        # Split the output into command sections
        sections = self.section_output(cleaned_data)

        # Parse the output
        for command, section in sections.items():
            pattern = SHOW_METRIC_DATA.get(command)['regex']
            if command == 'show server':
                self.parsed_data[command] = self.parse_show_server(section, pattern)
            else:
                try:
                    self.parsed_data[command] = self.parse_factory(section, pattern)
                except Exception as e:
                    self.log.error('Error parsing command %s: %s', command, e)
                    continue

        for command, metric_info in self.parsed_data.items():
            metric_keys = SHOW_METRIC_DATA.get(command)['metric_keys']
            tag_keys = SHOW_METRIC_DATA.get(command)['tags']
            metric_prefix = SHOW_METRIC_DATA.get(command)['metric_prefix']

            if command == 'show server':
                self.submit_metrics_factory(metric_prefix, metric_info, metric_keys, tag_keys)
            else:
                for metric_entry in metric_info:
                    self.submit_metrics_factory(metric_prefix, metric_entry, metric_keys, tag_keys)

    def parse_unit(self, value):
        match = unit_pattern.match(value)
        if match:
            return {'value': float(match.group('value')), 'unit': match.group('unit')}
        return value

    def parse_generic(self, value):
        try:
            return int(value)
        except ValueError:
            return value

    def parse_show_server(self, output, pattern):
        server_data = {}
        lines = output.strip().split('\n')

        rate_pattern = re.compile(r'(?P<value>\d+)\s*(?P<unit>\S+)')

        def parse_value(key, value):
            if key == 'server':
                version_match = re.search(r'\d+\.\d+\.\d+', value)
                if version_match:
                    server_data['version'] = version_match.group()
                server_data[key] = value
            elif key in ['topics', 'queues']:
                server_data[key] = int(value.split(' ')[0])
            elif "rate" in key:
                server_data[key] = parse_rate(value)
            elif any(metric in key for metric in metrics_with_units):
                server_data[key] = self.parse_unit(value)
            else:
                server_data[key] = self.parse_generic(value)

        def parse_rate(value):
            rate_data = {}
            rates = value.split(',')
            count_match = rate_pattern.match(rates[0].strip())
            unit_match = unit_pattern.match(rates[1].strip())
            if count_match and unit_match:
                rate_data["count"] = float(count_match.group('value'))
                rate_data["count_unit"] = count_match.group('unit')
                rate_data["size"] = float(unit_match.group('value'))
                rate_data["size_unit"] = unit_match.group('unit')
            return rate_data

        metrics_with_units = [
            'pending_message_size',
            'message_memory_usage',
            'message_memory_pooled',
            'synchronous_storage',
            'asynchronous_storage',
        ]

        for line in lines:
            match = pattern.match(line)
            if match:
                key = match.group('key').strip().lower().replace(' ', '_')
                value = match.group('value').strip()
                parse_value(key, value)

        return server_data

    def parse_factory(self, output, pattern):
        data = []
        lines = output.strip().split('\n')

        metrics_with_units = [
            'pending_messages_size',
            'pending_persistent_messages_size',
            'total_messages_size',
            'uncommitted_transactions_size',
            'messages_rate_size',
        ]

        for line in lines[1:]:
            match = pattern.match(line)
            if match:
                info = match.groupdict()
                if info.get('queue_name') == '>' or info.get('topic_name') == '>':
                    continue
                if info.get('user') == '<offline>':
                    info['user'] = 'offline'

                for key, value in info.items():
                    if key in metrics_with_units:
                        info[key] = self.parse_unit(value)
                    else:
                        if '$' in value:
                            value = value.replace('$', '')
                        info[key] = self.parse_generic(value)
                data.append(info)
        return data

    def submit_metrics_factory(self, prefix, metric_data, metric_names, tag_keys):

        tags = []
        for key in tag_keys:
            if prefix == 'server':
                # Add server tags to all metrics
                self.tags.append(f"server_{key}:{metric_data.get(key)}")
            else:
                if metric_data.get(key):
                    tags.append(f"{key}:{metric_data.get(key)}")

        tags.extend(self.tags)

        for metric_name in metric_names:
            metric_info = metric_data.get(metric_name)
            if metric_name in metric_data:
                if isinstance(metric_info, dict):
                    self.gauge(
                        f"{prefix}.{metric_name}", (metric_info['value'] * TO_BYTES[metric_info['unit']]), tags=tags
                    )
                else:
                    self.gauge(f"{prefix}.{metric_name}", metric_info, tags=tags)

    def section_output(self, output):
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

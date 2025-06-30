import re
import sys

from glustercli.cli import glusterfs_version, heal, peer, quota, snapshot, volume
from glustercli.cli.utils import GlusterCmdException


# Global variables for monkey patching
_USE_SUDO = True
_LOGGER = None

# Monkey patch glustercli to add sudo support and logging
# We'll patch it dynamically after import to avoid import errors
def _apply_glustercli_patch():
    """Apply monkey patch to glustercli's execute function"""
    try:
        # Try to find and patch the execute function in glustercli
        import glustercli.cli.utils as utils_module
        if hasattr(utils_module, 'execute'):
            original_execute = utils_module.execute
            
            def patched_execute(cmd, **kwargs):
                """Patched execute function that adds sudo support and logging"""
                global _USE_SUDO, _LOGGER
                
                # Prepend sudo if needed
                if _USE_SUDO and not cmd.startswith('sudo'):
                    cmd = 'sudo ' + cmd
                
                # Log the command being executed
                if _LOGGER:
                    _LOGGER.debug("Executing GlusterFS command: %s", cmd)
                
                try:
                    # Call the original execute function
                    result = original_execute(cmd, **kwargs)
                    
                    # Log the output
                    if _LOGGER and result:
                        output_lines = str(result).strip().split('\n')
                        if output_lines:
                            _LOGGER.debug("Command output (first 5 lines):")
                            for line in output_lines[:5]:
                                _LOGGER.debug("  %s", line)
                            if len(output_lines) > 5:
                                _LOGGER.debug("  ... (%d more lines)", len(output_lines) - 5)
                    
                    return result
                except Exception as e:
                    if _LOGGER:
                        _LOGGER.error("GlusterFS command failed: %s", str(e))
                    raise
            
            # Apply the patch
            utils_module.execute = patched_execute
            return True
    except (ImportError, AttributeError):
        # If we can't find the execute function, try alternative locations
        try:
            import glustercli
            # Look for execute in various possible locations
            for module_path in ['utils', 'cli.utils', 'cli']:
                try:
                    module = glustercli
                    for part in module_path.split('.'):
                        module = getattr(module, part)
                    if hasattr(module, 'execute'):
                        # Found it, apply patch here
                        original_execute = module.execute
                        
                        def patched_execute(cmd, **kwargs):
                            """Patched execute function that adds sudo support and logging"""
                            global _USE_SUDO, _LOGGER
                            
                            # Prepend sudo if needed
                            if _USE_SUDO and not cmd.startswith('sudo'):
                                cmd = 'sudo ' + cmd
                            
                            # Log the command being executed
                            if _LOGGER:
                                _LOGGER.debug("Executing GlusterFS command: %s", cmd)
                            
                            try:
                                # Call the original execute function
                                result = original_execute(cmd, **kwargs)
                                
                                # Log the output
                                if _LOGGER and result:
                                    output_lines = str(result).strip().split('\n')
                                    if output_lines:
                                        _LOGGER.debug("Command output (first 5 lines):")
                                        for line in output_lines[:5]:
                                            _LOGGER.debug("  %s", line)
                                        if len(output_lines) > 5:
                                            _LOGGER.debug("  ... (%d more lines)", len(output_lines) - 5)
                                
                                return result
                            except Exception as e:
                                if _LOGGER:
                                    _LOGGER.error("GlusterFS command failed: %s", str(e))
                                raise
                        
                        module.execute = patched_execute
                        return True
                except AttributeError:
                    continue
        except ImportError:
            pass
    
    return False


class Cluster(object):
    """The cluster object is the parent of nodes, bricks and volumes"""

    def __init__(self, options, logger, use_sudo):
        # Set global variables for the monkey patch
        global _USE_SUDO, _LOGGER
        _USE_SUDO = use_sudo
        _LOGGER = logger
        
        # Apply the monkey patch on first initialization
        _apply_glustercli_patch()
        
        # Store as instance attributes as well
        self.logger = logger
        self.use_sudo = use_sudo
        
        self.cluster_status = "Healthy"
        self.nodes = 0  # Number of nodes
        self.nodes_reachable = 0
        self.volume_count = 0
        self.volumes_started = 0
        self.volume_data = []
        self.glusterfs_version = glusterfs_version().split()[1]
        self.unit = options.units.upper() if options.units else 'H'
        self.volumes = options.volumes if hasattr(options, 'volumes') and options.volumes else None
        self.detail = options.alldata
        self.brickinfo = options.brickinfo
        self.displayquota = options.displayquota
        self.displaysnap = options.displaysnap
        self.output_mode = options.output_mode.lower() if options.output_mode else 'console' 

    def gather_data(self):
        try:
            peers = peer.pool()
            vols = volume.vollist()

            if self.volumes:
                # We have a list of volumes specified on command line
                self.volume_data = self._get_volume_details(self.volumes, vols)
            else:  # Get the details of all volumes
                self.volume_data = volume.status_detail(group_subvols=True)
        except GlusterCmdException as err:
            errcode, msg, u = err.args[0]
            print(msg, file=sys.stderr)
            exit(errcode)

        self.nodes = len(peers)
        for p in peers:
            self.nodes_reachable += 1 if p['connected'] == 'Connected' else 0
        if self.nodes_reachable < self.nodes:
            self.cluster_status = "Degraded"

        self.volume_count = len(self.volume_data)
        for v in self.volume_data:
            self.volumes_started += 1 if v['status'] == 'Started' else 0

        # Update the volume size and disk used
        self._update_volume_sizes()

        # If detail is requested, update quota, snapshot, and everything else
        if self.detail or self.displayquota:
            self._update_quota_info()

        # Snapshots
        if self.detail or self.displaysnap:
            self._update_snapshot_info()

        # Self-heal information, if any.
        self._update_heal_info()

    def _update_volume_sizes(self):
        """Update the volume information"""

        for v in self.volume_data:
            online = 0
            vol_used_percent = 0
            quota = ''
            voltype = ''  # Set only in case of arbiter volumes

            for subvol in v['subvols']:
                for brick in subvol['bricks']:
                    online += 1 if brick['online'] else 0
                    if v['type'].lower() == 'replicate' and brick['type'] == 'Arbiter':
                        voltype = ' - (Arbiter Volume)'

            vol_size = v['size_total']
            vol_size_free = v['size_free']

            # If the bricks are down, glusterd reports vol_size as 0 calculate
            # only if vol_size is available
            if vol_size > 0:
                vol_size_used = vol_size - vol_size_free
                vol_used_percent = (vol_size_used / vol_size) * 100
                # Convert to human readable format
                vol_size_h = self._readable_format(vol_size)
                vol_size_used_h = self._readable_format(vol_size_used)
                v['v_size'] = vol_size_h
                v['v_size_used'] = vol_size_used_h
                v['v_used_percent'] = "%.2f" % (vol_used_percent)
            v['online'] = online
            v['voltype'] = voltype

            # Is quota enabled?
            for opt in v['options']:
                if opt['name'] == 'features.quota':
                    quota = opt['value'].capitalize()
            v['quota'] = quota

    def _get_volume_details(self, display_vols, vols):
        matched_vols = []

        # Get the details of matched volumes
        for pat in display_vols:
            for v in vols:
                if v in matched_vols:
                    continue
                try:
                    if re.fullmatch(pat, v):
                        matched_vols.append(v)
                except Exception as err:
                    print("Invalid regex: %s. Try .* instead of *" % (err), file=sys.stderr)
                    exit(1)
        try:
            status = volume.status_detail(matched_vols, group_subvols=True)
        except GlusterCmdException as err:
            errcode, msg, u = err.args[0]
            print(msg, file=sys.stderr)
            exit(errcode)

        return status

    def _readable_format(self, size):
        KiB = 1024
        MiB = KiB * KiB
        GiB = MiB * KiB
        TiB = GiB * KiB
        PiB = TiB * KiB
        units = {'K': KiB, 'M': MiB, 'G': GiB, 'T': TiB, 'P': PiB}

        if self.unit == 'H':  # Human readable format
            for u in ['KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
                size /= KiB
                if size < KiB:
                    return "%.2f %s" % (round(size, 0), u)
        elif self.unit in units:  # Convert the size to specified units
            size /= units[self.unit]
            return "%.2f %siB" % (size, self.unit)
        else:
            print("Unknown unit %s, allowed units k/m/g/t/p/h" % (self.unit), file=sys.stderr)
            exit(1)

    def _update_quota_info(self):
        for vol in self.volume_data:
            quota_list = []
            if vol['quota']:
                try:
                    quota_list = quota.list_paths(vol['name'])
                except GlusterCmdException:
                    # If the volume is stopped we get an exception
                    pass
                for q in quota_list:
                    q['hard_limit'] = self._readable_format(float(q['hard_limit']))
                    q['used_space'] = self._readable_format(float(q['used_space']))
                    q['avail_space'] = self._readable_format(float(q['avail_space']))
                vol['quota_list'] = quota_list

    def _update_snapshot_info(self):
        # Update the volumes with their respective snapshots
        for _volume in self.volume_data:
            if _volume['snapshot_count'] > 0:
                _volume['snapshots'] = snapshot.info(volname=_volume['name'])

    def _update_heal_info(self):
        heal_fail = 0
        for _volume in self.volume_data:
            if _volume['status'].lower() == 'started':
                try:
                    _volume['healinfo'] = heal.info(_volume['name'])
                except GlusterCmdException:
                    heal_fail = 1
                    pass
        if heal_fail:
            print("Note: Unable to get self-heal status for one or more " "volumes", file=sys.stderr)

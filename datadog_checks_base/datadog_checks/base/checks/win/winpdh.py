# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from collections import defaultdict

import win32pdh
from six import iteritems, text_type
from six.moves import winreg

DATA_TYPE_INT = win32pdh.PDH_FMT_LONG
DATA_TYPE_DOUBLE = win32pdh.PDH_FMT_DOUBLE
DATA_POINT_INTERVAL = 0.10
SINGLE_INSTANCE_KEY = "__single_instance"


class WinPDHCounter(object):
    # store the dictionary of pdh counter names
    pdh_counter_dict = defaultdict(list)
    _use_en_counter_names = False

    def __init__(self, en_class_name, en_counter_name, log, instance_name=None, machine_name=None, precision=None):
        self.counterdict = {}
        self.logger = log
        self._counter_name = en_counter_name
        self._en_class_name = en_class_name
        self._instance_name = instance_name
        self._machine_name = machine_name
        self._is_single_instance = False

        if precision is None:
            self._precision = win32pdh.PDH_FMT_DOUBLE
        else:
            self._precision = precision

        class_name_index_list = []
        try:
            self._get_counter_dictionary()
            class_name_index_list = WinPDHCounter.pdh_counter_dict[en_class_name]
        except WindowsError:
            WinPDHCounter._use_en_counter_names = True
            self.logger.warning("Unable to get counter translations; attempting default English names")
        except Exception as e:
            self.logger.error("Exception loading counter strings %s", str(e))
            raise

        if WinPDHCounter._use_en_counter_names:
            self._class_name = en_class_name
        else:
            if len(class_name_index_list) == 0:
                self.logger.warning("Class %s was not in counter name list, attempting english counter", en_class_name)
                self._class_name = en_class_name
            else:
                if len(class_name_index_list) > 1:
                    self.logger.warning(
                        "Class %s had multiple (%d) indices, using first", en_class_name, len(class_name_index_list)
                    )
                self._class_name = win32pdh.LookupPerfNameByIndex(None, int(class_name_index_list[0]))

        self.hq = win32pdh.OpenQuery()
        self.collect_counters()

        if len(self.counterdict) == 0:
            raise AttributeError("No valid counters to report")

    def __del__(self):
        try:
            win32pdh.CloseQuery(self.hq)
        except AttributeError:
            # An error occurred during instantiation before a query was opened.
            pass

    def is_single_instance(self):
        return self._is_single_instance

    @property
    def class_name(self):
        """Returns the counter class name. The value is localized to the system but falls back to the english
        class name if the counter translations can't be fetched."""
        return self._class_name

    @property
    def english_class_name(self):
        """Always return the english version of the counter class name."""
        return self._en_class_name

    def get_single_value(self):
        if not self.is_single_instance():
            raise ValueError('counter is not single instance %s %s' % (self.class_name, self._counter_name))

        vals = self.get_all_values()
        return vals[SINGLE_INSTANCE_KEY]

    def get_all_values(self):
        ret = {}

        # self will retrieve the list of all object names in the class (i.e. all the network interface
        # names in the class "network interface"
        win32pdh.CollectQueryData(self.hq)

        for inst, counter_handle in iteritems(self.counterdict):
            try:
                t, val = win32pdh.GetFormattedCounterValue(counter_handle, self._precision)
                ret[inst] = val
            except Exception:
                # exception usually means self type needs two data points to calculate. Wait
                # a bit and try again
                time.sleep(DATA_POINT_INTERVAL)
                win32pdh.CollectQueryData(self.hq)
                # if we get exception self time, just return it up
                t, val = win32pdh.GetFormattedCounterValue(counter_handle, self._precision)
                ret[inst] = val
        return ret

    def _get_counter_dictionary(self):
        if WinPDHCounter.pdh_counter_dict:
            # already populated
            return
        if WinPDHCounter._use_en_counter_names:
            # already found out the registry isn't there
            return

        try:
            val, t = winreg.QueryValueEx(winreg.HKEY_PERFORMANCE_DATA, "Counter 009")
        except:  # noqa: E722, B001
            self.logger.error("Windows error; performance counters not found in registry")
            self.logger.error("Performance counters may need to be rebuilt.")
            raise

        # val is an array of strings.  The underlying win32 API returns a list of strings
        # which is the counter name, counter index, counter name, counter index (in windows,
        # a multi-string value)
        #
        # the python implementation translates the multi-string value into an array of strings.
        # the array of strings then becomes
        # array[0] = counter_index_1
        # array[1] = counter_name_1
        # array[2] = counter_index_2
        # array[3] = counter_name_2
        #
        # see https://support.microsoft.com/en-us/help/287159/using-pdh-apis-correctly-in-a-localized-language
        # for more detail

        # create a table of the keys to the counter index, because we want to look up
        # by counter name. Some systems may have an odd number of entries, don't
        # accidentally index at val[len(val]
        for idx in range(0, len(val) - 1, 2):
            WinPDHCounter.pdh_counter_dict[val[idx + 1]].append(val[idx])

    def _make_counter_path(self, machine_name, en_counter_name, instance_name, counters):
        """
        When handling non english versions, the counters don't work quite as documented.
        This is because strings like "Bytes Sent/sec" might appear multiple times in the
        english master, and might not have mappings for each index.

        Search each index, and make sure the requested counter name actually appears in
        the list of available counters; that's the counter we'll use.
        """
        path = ""
        if WinPDHCounter._use_en_counter_names:
            """
            In this case, we don't have any translations.  Just attempt to make the
            counter path
            """
            try:
                path = win32pdh.MakeCounterPath(
                    (machine_name, self.class_name, instance_name, None, 0, en_counter_name)
                )
                self.logger.debug("Successfully created English-only path")
            except Exception as e:  # noqa: E722, B001
                self.logger.warning("Unable to create English-only path %s", e)
                raise
            return path

        counter_name_index_list = WinPDHCounter.pdh_counter_dict[en_counter_name]

        for index in counter_name_index_list:
            c = win32pdh.LookupPerfNameByIndex(None, int(index))
            if c is None or len(c) == 0:
                self.logger.debug("Index %s not found, skipping", index)
                continue

            # check to see if this counter is in the list of counters for this class
            if c not in counters:
                try:
                    self.logger.debug("Index %s counter %s not in counter list", index, text_type(c))
                except:  # noqa: E722, B001
                    # some unicode characters are not translatable here.  Don't fail just
                    # because we couldn't log
                    self.logger.debug("Index %s not in counter list", index)

                continue

            # see if we can create a counter
            try:
                path = win32pdh.MakeCounterPath((machine_name, self.class_name, instance_name, None, 0, c))
                break
            except:  # noqa: E722, B001
                try:
                    self.logger.info("Unable to make path with counter %s, trying next available", text_type(c))
                except:  # noqa: E722, B001
                    self.logger.info("Unable to make path with counter index %s, trying next available", index)
        return path

    def collect_counters(self):
        counters, instances = win32pdh.EnumObjectItems(
            None, self._machine_name, self.class_name, win32pdh.PERF_DETAIL_WIZARD
        )
        if self._instance_name is None and len(instances) > 0:
            all_instances = set()
            for inst in instances:
                path = self._make_counter_path(self._machine_name, self._counter_name, inst, counters)
                if not path:
                    continue
                all_instances.add(inst)

                try:
                    if inst not in self.counterdict:
                        self.logger.debug('Adding instance `%s`', inst)
                        self.counterdict[inst] = win32pdh.AddCounter(self.hq, path)
                except:  # noqa: E722, B001
                    self.logger.fatal(
                        "Failed to create counter.  No instances of %s\\%s" % (self.class_name, self._counter_name)
                    )

            expired_instances = set(self.counterdict) - all_instances
            for inst in expired_instances:
                self.logger.debug('Removing expired instance `%s`', inst)
                del self.counterdict[inst]
        else:
            if self._instance_name is not None:
                # check to see that it's valid
                if len(instances) <= 0:
                    self.logger.error(
                        "%s doesn't seem to be a multi-instance counter, but asked for specific instance %s",
                        self.class_name,
                        self._instance_name,
                    )
                    raise AttributeError("%s is not a multi-instance counter" % self.class_name)
                if self._instance_name not in instances:
                    self.logger.error("%s is not a counter instance in %s", self._instance_name, self.class_name)
                    raise AttributeError("%s is not an instance of %s" % (self._instance_name, self.class_name))

            path = self._make_counter_path(self._machine_name, self._counter_name, self._instance_name, counters)
            if not path:
                self.logger.warning("Empty path returned")
            elif win32pdh.ValidatePath(path) != 0:
                # Multi-instance counter with no instances presently
                pass
            else:
                try:
                    if SINGLE_INSTANCE_KEY not in self.counterdict:
                        self.logger.debug('Adding single instance for path `%s`', path)
                        self.counterdict[SINGLE_INSTANCE_KEY] = win32pdh.AddCounter(self.hq, path)
                except:  # noqa: E722, B001
                    self.logger.fatal(
                        "Failed to create counter.  No instances of %s\\%s" % (self.class_name, self._counter_name)
                    )
                    raise
                self._is_single_instance = True

# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
from collections import defaultdict
from contextlib import closing

import pymysql
from six import PY3, iteritems

from datadog_checks.base import is_affirmative
from datadog_checks.base.log import get_check_logger
from datadog_checks.mysql.cursor import CommenterCursor

from .collection_utils import collect_scalar
from .const import OPTIONAL_INNODB_VARS

if PY3:
    long = int


def _are_values_numeric(array):
    return all(v.isdigit() for v in array)


class InnoDBMetrics(object):
    def __init__(self):
        self.log = get_check_logger()

    def get_stats_from_innodb_status(self, db):
        # There are a number of important InnoDB metrics that are reported in
        # InnoDB status but are not otherwise present as part of the STATUS
        # variables in MySQL. Majority of these metrics are reported though
        # as a part of STATUS variables in Percona Server and MariaDB.
        # Requires querying user to have PROCESS privileges.
        try:
            with closing(db.cursor(CommenterCursor)) as cursor:
                cursor.execute("SHOW /*!50000 ENGINE*/ INNODB STATUS")
        except (pymysql.err.InternalError, pymysql.err.OperationalError, pymysql.err.NotSupportedError) as e:
            self.log.warning(
                "Privilege error or engine unavailable accessing the INNODB status tables (must grant PROCESS): %s", e
            )
            return {}
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            self.log.warning(
                "Unicode error while getting INNODB status "
                "(typically harmless, but if this warning is frequent metric collection could be impacted): %s",
                str(e),
            )
            return {}

        if cursor.rowcount < 1:
            # No data from SHOW ENGINE STATUS, even though the engine is enabled.
            # EG: This could be an Aurora Read Instance
            self.log.warning(
                """'SHOW ENGINE INNODB STATUS' returned no data.
                If you are running an Aurora Read Instance, \
                this is expected and you should disable the innodb metrics collection"""
            )
            return {}

        innodb_status = cursor.fetchone()
        innodb_status_text = innodb_status[2]

        results = defaultdict(int)

        # Here we now parse InnoDB STATUS one line at a time
        # This is heavily inspired by the Percona monitoring plugins work
        txn_seen = False
        prev_line = ''
        # Only return aggregated buffer pool metrics
        buffer_id = -1
        for line in innodb_status_text.splitlines():
            line = line.strip()
            row = re.split(" +", line)
            row = [item.strip(',') for item in row]
            row = [item.strip(';') for item in row]
            row = [item.strip('[') for item in row]
            row = [item.strip(']') for item in row]

            if line.startswith('---BUFFER POOL'):
                buffer_id = long(row[2])

            # SEMAPHORES
            if line.find('Mutex spin waits') == 0:
                # Mutex spin waits 79626940, rounds 157459864, OS waits 698719
                # Mutex spin waits 0, rounds 247280272495, OS waits 316513438
                results['Innodb_mutex_spin_waits'] = long(row[3])
                results['Innodb_mutex_spin_rounds'] = long(row[5])
                results['Innodb_mutex_os_waits'] = long(row[8])
            elif line.find('RW-shared spins') == 0 and line.find(';') > 0:
                # RW-shared spins 3859028, OS waits 2100750; RW-excl spins
                # 4641946, OS waits 1530310
                results['Innodb_s_lock_spin_waits'] = long(row[2])
                results['Innodb_x_lock_spin_waits'] = long(row[8])
                results['Innodb_s_lock_os_waits'] = long(row[5])
                results['Innodb_x_lock_os_waits'] = long(row[11])
            elif line.find('RW-shared spins') == 0 and line.find('; RW-excl spins') == -1:
                # Post 5.5.17 SHOW ENGINE INNODB STATUS syntax
                # RW-shared spins 604733, rounds 8107431, OS waits 241268
                results['Innodb_s_lock_spin_waits'] = long(row[2])
                results['Innodb_s_lock_spin_rounds'] = long(row[4])
                results['Innodb_s_lock_os_waits'] = long(row[7])
            elif line.find('RW-excl spins') == 0:
                # Post 5.5.17 SHOW ENGINE INNODB STATUS syntax
                # RW-excl spins 604733, rounds 8107431, OS waits 241268
                results['Innodb_x_lock_spin_waits'] = long(row[2])
                results['Innodb_x_lock_spin_rounds'] = long(row[4])
                results['Innodb_x_lock_os_waits'] = long(row[7])
            elif line.find('seconds the semaphore:') > 0:
                # --Thread 907205 has waited at handler/ha_innodb.cc line 7156 for 1.00 seconds the semaphore:
                results['Innodb_semaphore_waits'] += 1
                results['Innodb_semaphore_wait_time'] += long(float(row[9])) * 1000

            # TRANSACTIONS
            elif line.find('Trx id counter') == 0:
                # The beginning of the TRANSACTIONS section: start counting
                # transactions
                # Trx id counter 0 1170664159
                # Trx id counter 861B144C
                txn_seen = True
            elif line.find('History list length') == 0:
                # History list length 132
                results['Innodb_history_list_length'] = long(row[3])
            elif txn_seen and line.find('---TRANSACTION') == 0:
                # ---TRANSACTION 0, not started, process no 13510, OS thread id 1170446656
                results['Innodb_current_transactions'] += 1
                if line.find('ACTIVE') > 0:
                    results['Innodb_active_transactions'] += 1
            elif line.find('read views open inside InnoDB') > 0:
                # 1 read views open inside InnoDB
                results['Innodb_read_views'] = long(row[0])
            elif line.find('mysql tables in use') == 0:
                # mysql tables in use 2, locked 2
                results['Innodb_tables_in_use'] += long(row[4])
                results['Innodb_locked_tables'] += long(row[6])
            elif txn_seen and line.find('lock struct(s)') > 0:
                # 23 lock struct(s), heap size 3024, undo log entries 27
                # LOCK WAIT 12 lock struct(s), heap size 3024, undo log entries 5
                # LOCK WAIT 2 lock struct(s), heap size 368
                if line.find('LOCK WAIT') == 0:
                    results['Innodb_lock_structs'] += long(row[2])
                    results['Innodb_locked_transactions'] += 1
                elif line.find('ROLLING BACK') == 0:
                    # ROLLING BACK 127539 lock struct(s), heap size 15201832,
                    # 4411492 row lock(s), undo log entries 1042488
                    results['Innodb_lock_structs'] += long(row[2])
                else:
                    results['Innodb_lock_structs'] += long(row[0])

            # FILE I/O
            elif line.find(' OS file reads, ') > 0:
                # 8782182 OS file reads, 15635445 OS file writes, 947800 OS
                # fsyncs
                results['Innodb_os_file_reads'] = long(row[0])
                results['Innodb_os_file_writes'] = long(row[4])
                results['Innodb_os_file_fsyncs'] = long(row[8])
            elif line.find('Pending normal aio reads:') == 0:
                try:
                    if len(row) == 8:
                        # (len(row) == 8)  Pending normal aio reads: 0, aio writes: 0,
                        results['Innodb_pending_normal_aio_reads'] = long(row[4])
                        results['Innodb_pending_normal_aio_writes'] = long(row[7])
                    elif len(row) == 14:
                        # (len(row) == 14) Pending normal aio reads: 0 [0, 0] , aio writes: 0 [0, 0] ,
                        results['Innodb_pending_normal_aio_reads'] = long(row[4])
                        results['Innodb_pending_normal_aio_writes'] = long(row[10])
                    elif len(row) == 16:
                        # (len(row) == 16) Pending normal aio reads: [0, 0, 0, 0] , aio writes: [0, 0, 0, 0] ,
                        if _are_values_numeric(row[4:8]) and _are_values_numeric(row[11:15]):
                            results['Innodb_pending_normal_aio_reads'] = (
                                long(row[4]) + long(row[5]) + long(row[6]) + long(row[7])
                            )
                            results['Innodb_pending_normal_aio_writes'] = (
                                long(row[11]) + long(row[12]) + long(row[13]) + long(row[14])
                            )

                        # (len(row) == 16) Pending normal aio reads: 0 [0, 0, 0, 0] , aio writes: 0 [0, 0] ,
                        elif _are_values_numeric(row[4:9]) and _are_values_numeric(row[12:15]):
                            results['Innodb_pending_normal_aio_reads'] = long(row[4])
                            results['Innodb_pending_normal_aio_writes'] = long(row[12])
                        else:
                            self.log.warning("Can't parse result line %s", line)
                    elif len(row) == 18:
                        # (len(row) == 18) Pending normal aio reads: 0 [0, 0, 0, 0] , aio writes: 0 [0, 0, 0, 0] ,
                        results['Innodb_pending_normal_aio_reads'] = long(row[4])
                        results['Innodb_pending_normal_aio_writes'] = long(row[12])
                    elif len(row) == 22:
                        # (len(row) == 22)
                        # Pending normal aio reads: 0 [0, 0, 0, 0, 0, 0, 0, 0] , aio writes: 0 [0, 0, 0, 0] ,
                        results['Innodb_pending_normal_aio_reads'] = long(row[4])
                        results['Innodb_pending_normal_aio_writes'] = long(row[16])
                except ValueError as e:
                    self.log.warning("Can't parse result line %s: %s", line, e)
            elif line.find('ibuf aio reads') == 0:
                #  ibuf aio reads: 0, log i/o's: 0, sync i/o's: 0
                #  or ibuf aio reads:, log i/o's:, sync i/o's:
                if len(row) == 10:
                    results['Innodb_pending_ibuf_aio_reads'] = long(row[3])
                    results['Innodb_pending_aio_log_ios'] = long(row[6])
                    results['Innodb_pending_aio_sync_ios'] = long(row[9])
                elif len(row) == 7:
                    results['Innodb_pending_ibuf_aio_reads'] = 0
                    results['Innodb_pending_aio_log_ios'] = 0
                    results['Innodb_pending_aio_sync_ios'] = 0
            elif line.find('Pending flushes (fsync)') == 0:
                if len(row) == 4:
                    # Pending flushes (fsync): 0
                    results['Innodb_pending_buffer_pool_flushes'] = long(row[3])
                else:
                    # Pending flushes (fsync) log: 0; buffer pool: 0
                    results['Innodb_pending_log_flushes'] = long(row[4])
                    results['Innodb_pending_buffer_pool_flushes'] = long(row[7])

            # INSERT BUFFER AND ADAPTIVE HASH INDEX
            elif line.find('Ibuf for space 0: size ') == 0:
                # Older InnoDB code seemed to be ready for an ibuf per tablespace.  It
                # had two lines in the output.  Newer has just one line, see below.
                # Ibuf for space 0: size 1, free list len 887, seg size 889, is not empty
                # Ibuf for space 0: size 1, free list len 887, seg size 889,
                results['Innodb_ibuf_size'] = long(row[5])
                results['Innodb_ibuf_free_list'] = long(row[9])
                results['Innodb_ibuf_segment_size'] = long(row[12])
            elif line.find('Ibuf: size ') == 0:
                # Ibuf: size 1, free list len 4634, seg size 4636,
                results['Innodb_ibuf_size'] = long(row[2])
                results['Innodb_ibuf_free_list'] = long(row[6])
                results['Innodb_ibuf_segment_size'] = long(row[9])

                if line.find('merges') > -1:
                    results['Innodb_ibuf_merges'] = long(row[10])
            elif line.find(', delete mark ') > 0 and prev_line.find('merged operations:') == 0:
                # Output of show engine innodb status has changed in 5.5
                # merged operations:
                # insert 593983, delete mark 387006, delete 73092
                results['Innodb_ibuf_merged_inserts'] = long(row[1])
                results['Innodb_ibuf_merged_delete_marks'] = long(row[4])
                results['Innodb_ibuf_merged_deletes'] = long(row[6])
                results['Innodb_ibuf_merged'] = (
                    results['Innodb_ibuf_merged_inserts']
                    + results['Innodb_ibuf_merged_delete_marks']
                    + results['Innodb_ibuf_merged_deletes']
                )
            elif line.find(' merged recs, ') > 0:
                # 19817685 inserts, 19817684 merged recs, 3552620 merges
                results['Innodb_ibuf_merged_inserts'] = long(row[0])
                results['Innodb_ibuf_merged'] = long(row[2])
                results['Innodb_ibuf_merges'] = long(row[5])
            elif line.find('Hash table size ') == 0:
                # In some versions of InnoDB, the used cells is omitted.
                # Hash table size 4425293, used cells 4229064, ....
                # Hash table size 57374437, node heap has 72964 buffer(s) <--
                # no used cells
                results['Innodb_hash_index_cells_total'] = long(row[3])
                results['Innodb_hash_index_cells_used'] = long(row[6]) if line.find('used cells') > 0 else 0

            # LOG
            elif line.find(" log i/o's done, ") > 0:
                # 3430041 log i/o's done, 17.44 log i/o's/second
                # 520835887 log i/o's done, 17.28 log i/o's/second, 518724686
                # syncs, 2980893 checkpoints
                results['Innodb_log_writes'] = long(row[0])
            elif line.find(" pending log writes, ") > 0:
                # 0 pending log writes, 0 pending chkp writes
                results['Innodb_pending_log_writes'] = long(row[0])
                results['Innodb_pending_checkpoint_writes'] = long(row[4])
            elif line.find("Log sequence number") == 0:
                # This number is NOT printed in hex in InnoDB plugin.
                # Log sequence number 272588624
                results['Innodb_lsn_current'] = long(row[3])
            elif line.find("Log flushed up to") == 0:
                # This number is NOT printed in hex in InnoDB plugin.
                # Log flushed up to   272588624
                results['Innodb_lsn_flushed'] = long(row[4])
            elif line.find("Last checkpoint at") == 0:
                # Last checkpoint at  272588624
                results['Innodb_lsn_last_checkpoint'] = long(row[3])

            # BUFFER POOL AND MEMORY
            elif line.find("Total memory allocated") == 0 and line.find("in additional pool allocated") > 0:
                # Total memory allocated 29642194944; in additional pool allocated 0
                # Total memory allocated by read views 96
                results['Innodb_mem_total'] = long(row[3])
                results['Innodb_mem_additional_pool'] = long(row[8])
            elif line.find('Adaptive hash index ') == 0:
                #   Adaptive hash index 1538240664     (186998824 + 1351241840)
                results['Innodb_mem_adaptive_hash'] = long(row[3])
            elif line.find('Page hash           ') == 0:
                #   Page hash           11688584
                results['Innodb_mem_page_hash'] = long(row[2])
            elif line.find('Dictionary cache    ') == 0:
                #   Dictionary cache    145525560      (140250984 + 5274576)
                results['Innodb_mem_dictionary'] = long(row[2])
            elif line.find('File system         ') == 0:
                #   File system         313848         (82672 + 231176)
                results['Innodb_mem_file_system'] = long(row[2])
            elif line.find('Lock system         ') == 0:
                #   Lock system         29232616       (29219368 + 13248)
                results['Innodb_mem_lock_system'] = long(row[2])
            elif line.find('Recovery system     ') == 0:
                #   Recovery system     0      (0 + 0)
                results['Innodb_mem_recovery_system'] = long(row[2])
            elif line.find('Threads             ') == 0:
                #   Threads             409336         (406936 + 2400)
                results['Innodb_mem_thread_hash'] = long(row[1])
            elif line.find("Buffer pool size ") == 0:
                # The " " after size is necessary to avoid matching the wrong line:
                # Buffer pool size        1769471
                # Buffer pool size, bytes 28991012864
                if buffer_id == -1:
                    results['Innodb_buffer_pool_pages_total'] = long(row[3])
            elif line.find("Free buffers") == 0:
                # Free buffers            0
                if buffer_id == -1:
                    results['Innodb_buffer_pool_pages_free'] = long(row[2])
            elif line.find("Database pages") == 0:
                # Database pages          1696503
                if buffer_id == -1:
                    results['Innodb_buffer_pool_pages_data'] = long(row[2])

            elif line.find("Modified db pages") == 0:
                # Modified db pages       160602
                if buffer_id == -1:
                    results['Innodb_buffer_pool_pages_dirty'] = long(row[3])
            elif line.find("Pages read ahead") == 0:
                # Must do this BEFORE the next test, otherwise it'll get fooled by this
                # line from the new plugin:
                # Pages read ahead 0.00/s, evicted without access 0.06/s
                pass
            elif line.find("Pages read") == 0:
                # Pages read 15240822, created 1770238, written 21705836
                if buffer_id == -1:
                    results['Innodb_pages_read'] = long(row[2])
                    results['Innodb_pages_created'] = long(row[4])
                    results['Innodb_pages_written'] = long(row[6])

            # ROW OPERATIONS
            elif line.find('Number of rows inserted') == 0:
                # Number of rows inserted 50678311, updated 66425915, deleted
                # 20605903, read 454561562
                results['Innodb_rows_inserted'] = long(row[4])
                results['Innodb_rows_updated'] = long(row[6])
                results['Innodb_rows_deleted'] = long(row[8])
                results['Innodb_rows_read'] = long(row[10])
            elif line.find(" queries inside InnoDB, ") > 0:
                # 0 queries inside InnoDB, 0 queries in queue
                results['Innodb_queries_inside'] = long(row[0])
                results['Innodb_queries_queued'] = long(row[4])

            prev_line = line

        # We need to calculate this metric separately
        try:
            results['Innodb_checkpoint_age'] = results['Innodb_lsn_current'] - results['Innodb_lsn_last_checkpoint']
        except KeyError as e:
            self.log.error("Not all InnoDB LSN metrics available, unable to compute: %s", e)

        # Finally we change back the metrics values to string to make the values
        # consistent with how they are reported by SHOW GLOBAL STATUS
        for metric, value in list(iteritems(results)):
            results[metric] = str(value)

        return results

    def process_innodb_stats(self, results, options, metrics):
        innodb_keys = [
            'Innodb_page_size',
            'Innodb_buffer_pool_pages_data',
            'Innodb_buffer_pool_pages_dirty',
            'Innodb_buffer_pool_pages_total',
            'Innodb_buffer_pool_pages_free',
        ]

        for inno_k in innodb_keys:
            results[inno_k] = collect_scalar(inno_k, results)

        try:
            innodb_page_size = results['Innodb_page_size']
            innodb_buffer_pool_pages_used = (
                results['Innodb_buffer_pool_pages_total'] - results['Innodb_buffer_pool_pages_free']
            )

            if 'Innodb_buffer_pool_bytes_data' not in results:
                results['Innodb_buffer_pool_bytes_data'] = results['Innodb_buffer_pool_pages_data'] * innodb_page_size

            if 'Innodb_buffer_pool_bytes_dirty' not in results:
                results['Innodb_buffer_pool_bytes_dirty'] = results['Innodb_buffer_pool_pages_dirty'] * innodb_page_size

            if 'Innodb_buffer_pool_bytes_free' not in results:
                results['Innodb_buffer_pool_bytes_free'] = results['Innodb_buffer_pool_pages_free'] * innodb_page_size

            if 'Innodb_buffer_pool_bytes_total' not in results:
                results['Innodb_buffer_pool_bytes_total'] = results['Innodb_buffer_pool_pages_total'] * innodb_page_size

            if 'Innodb_buffer_pool_pages_utilization' not in results:
                results['Innodb_buffer_pool_pages_utilization'] = (
                    innodb_buffer_pool_pages_used / results['Innodb_buffer_pool_pages_total']
                )

            if 'Innodb_buffer_pool_bytes_used' not in results:
                results['Innodb_buffer_pool_bytes_used'] = innodb_buffer_pool_pages_used * innodb_page_size
        except (KeyError, TypeError) as e:
            self.log.error("Not all InnoDB buffer pool metrics are available, unable to compute: %s", e)

        if is_affirmative(options.get('extra_innodb_metrics', False)):
            self.log.debug("Collecting Extra Innodb Metrics")
            metrics.update(OPTIONAL_INNODB_VARS)

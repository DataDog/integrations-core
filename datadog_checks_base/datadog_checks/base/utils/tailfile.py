# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import binascii
import os
from stat import ST_INO, ST_SIZE

from .common import ensure_bytes


class TailFile(object):

    CRC_SIZE = 16

    def __init__(self, logger, path, callback):
        self._path = path
        self._f = None
        self._inode = None
        self._size = 0
        self._crc = None
        self._log = logger
        self._callback = callback

    def _open_file(self, move_end=False, pos=False):

        already_open = False
        # close and reopen to handle logrotate
        if self._f is not None:
            self._f.close()
            self._f = None
            already_open = True

        stat = os.stat(self._path)
        inode = stat[ST_INO]
        size = stat[ST_SIZE]

        # Compute CRC of the beginning of the file
        crc = None
        if size >= self.CRC_SIZE:
            tmp_file = open(self._path, 'r')
            data = ensure_bytes(tmp_file.read(self.CRC_SIZE))
            crc = binascii.crc32(data)

        self._log.debug(
            "Open file. path=%s, cur_inode=%s, new_inode=%s, cur_size=%s, new_size=%s, move_end=%s, pos=%s",
            self._path,
            self._inode,
            inode,
            self._size,
            size,
            move_end,
            pos,
        )

        if already_open:
            # Check if file has been removed
            if self._inode is not None and inode != self._inode:
                self._log.debug("File removed, reopening")
                move_end = False
                pos = False

            # Check if file has been truncated
            elif self._size > 0 and size < self._size:
                self._log.debug("File truncated, reopening")
                move_end = False
                pos = False

            # Check if file has been truncated and too much data has
            # alrady been written (copytruncate and opened files...)
            if size >= self.CRC_SIZE and self._crc is not None and crc != self._crc:
                self._log.debug("Beginning of file modified, reopening")
                move_end = False
                pos = False

        self._inode = inode
        self._size = size
        self._crc = crc

        self._f = open(self._path, 'r')
        if move_end:
            self._log.debug("Opening file %s", self._path)
            self._f.seek(0, os.SEEK_END)
        elif pos:
            self._log.debug("Reopening file %s at %s", self._path, pos)
            self._f.seek(pos)

        return True

    def tail(self, line_by_line=True, move_end=True):
        """Read line-by-line and run callback on each line.
        line_by_line: yield each time a callback has returned True
        move_end: start from the last line of the log"""
        try:
            self._open_file(move_end=move_end)

            while True:
                pos = self._f.tell()
                line = self._f.readline()
                if line:
                    line = line.strip(chr(0))  # a truncate may have create holes in the file
                    if self._callback(line.rstrip("\n")):
                        if line_by_line:
                            yield True
                            pos = self._f.tell()
                            self._open_file(move_end=False, pos=pos)
                        else:
                            continue
                    else:
                        continue
                else:
                    yield True
                    assert pos == self._f.tell()
                    self._open_file(move_end=False, pos=pos)

        except Exception as e:
            # log but survive
            self._log.exception(e)
            raise StopIteration(e)

    def close(self):
        if self._f:
            self._f.close()
            self._f = None

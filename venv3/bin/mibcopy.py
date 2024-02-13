#!/Users/ben.goldberg/go/src/github.com/DataDog/integrations-core/venv3/bin/python3
#
# This file is part of pysmi software.
#
# Copyright (c) 2015-2019, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pysmi/license.html
#
# SNMP SMI/MIB copying tool
#
import os
import sys
import getopt
import shutil
from datetime import datetime
from pysmi.reader import FileReader, getReadersFromUrls
from pysmi.writer import CallbackWriter
from pysmi.parser import SmiV1CompatParser
from pysmi.codegen import JsonCodeGen
from pysmi.compiler import MibCompiler
from pysmi import debug
from pysmi import error

# sysexits.h
EX_OK = 0
EX_USAGE = 64
EX_SOFTWARE = 70

# Defaults
quietFlag = False
verboseFlag = False
mibSources = []
dstDirectory = None
cacheDirectory = ''
dryrunFlag = False
ignoreErrorsFlag = False

helpMessage = """\
Usage: %s [--help]
      [--version]
      [--verbose]
      [--quiet]
      [--debug=<%s>]
      [--mib-source=<URI>]
      [--cache-directory=<DIRECTORY>]
      [--ignore-errors]
      [--dry-run]
      <SOURCE [SOURCE...]> <DESTINATION>
Where:
    URI      - file, zip, http, https, ftp, sftp schemes are supported.
               Use @mib@ placeholder token in URI to refer directly to
               the required MIB module when source does not support
               directory listing (e.g. HTTP).
""" % (
    sys.argv[0],
    '|'.join([x for x in sorted(debug.flagMap)])
)

# TODO(etingof): add the option to copy MIBs into enterprise-indexed subdirs

try:
    opts, inputMibs = getopt.getopt(
        sys.argv[1:], 'hv',
        ['help', 'version', 'verbose', 'quiet', 'debug=',
         'mib-source=', 'mib-stub=',
         'cache-directory=', 'ignore-errors', 'dry-run']
    )

except getopt.GetoptError:
    sys.exit(EX_USAGE)

for opt in opts:
    if opt[0] == '-h' or opt[0] == '--help':
        sys.stderr.write("""\
Synopsis:
  SNMP SMI/MIB files copying tool. When given MIB file(s) or directory(ies)
  on input and a destination directory, the tool parses MIBs to figure out
  their canonical MIB module name and the latest revision date, then
  copies MIB module on input into the destination directory under its
  MIB module name *if* there is no such file already or its revision date
  is older.

Documentation:
  http://snmplabs.com/pysmi
%s
""" % helpMessage)
        sys.exit(EX_OK)

    if opt[0] == '-v' or opt[0] == '--version':
        from pysmi import __version__

        sys.stderr.write("""\
SNMP SMI/MIB library version %s, written by Ilya Etingof <etingof@gmail.com>
Python interpreter: %s
Software documentation and support at http://snmplabs.com/pysmi
%s
""" % (__version__, sys.version, helpMessage))
        sys.exit(EX_OK)

    if opt[0] == '--quiet':
        quietFlag = True

    if opt[0] == '--verbose':
        verboseFlag = True

    if opt[0] == '--debug':
        debug.setLogger(debug.Debug(*opt[1].split(',')))

    if opt[0] == '--mib-source':
        mibSources.append(opt[1])

    if opt[0] == '--cache-directory':
        cacheDirectory = opt[1]

    if opt[0] == '--ignore-errors':
        ignoreErrorsFlag = True

if not mibSources:
    mibSources = ['file:///usr/share/snmp/mibs',
                  'http://mibs.snmplabs.com/asn1/@mib@']

if len(inputMibs) < 2:
    sys.stderr.write('ERROR: MIB source and/or destination arguments not given\r\n%s\r\n' % helpMessage)
    sys.exit(EX_USAGE)

dstDirectory = inputMibs.pop()

if os.path.exists(dstDirectory) and not os.path.isdir(dstDirectory):
    sys.stderr.write('ERROR: given destination is not a directory\r\n%s\r\n' % helpMessage)
    sys.exit(EX_USAGE)

try:
    os.makedirs(dstDirectory, mode=0o755)

except OSError:
    pass

# Compiler infrastructure

codeGenerator = JsonCodeGen()

mibParser = SmiV1CompatParser(tempdir=cacheDirectory)

fileWriter = CallbackWriter(lambda *x: None)


def getMibRevision(mibDir, mibFile):

    mibCompiler = MibCompiler(
        mibParser,
        codeGenerator,
        fileWriter
    )

    mibCompiler.addSources(
        FileReader(mibDir, recursive=False, ignoreErrors=ignoreErrorsFlag),
        *getReadersFromUrls(*mibSources)
    )

    try:
        processed = mibCompiler.compile(
            mibFile, **dict(noDeps=True, rebuild=True, fuzzyMatching=False, ignoreErrors=ignoreErrorsFlag)
        )

    except error.PySmiError:
        sys.stderr.write('ERROR: %s\r\n' % sys.exc_info()[1])
        sys.exit(EX_SOFTWARE)

    for canonicalMibName in processed:
        if (processed[canonicalMibName] == 'compiled' and
                processed[canonicalMibName].path == 'file://' + os.path.join(mibDir, mibFile)):

            try:
                revision = datetime.strptime(processed[canonicalMibName].revision, '%Y-%m-%d %H:%M')

            except Exception:
                revision = datetime.fromtimestamp(0)

            return canonicalMibName, revision

    raise error.PySmiError('Can\'t read or parse MIB "%s"' % os.path.join(mibDir, mibFile))


def shortenPath(path, maxLength=45):
    if len(path) > maxLength:
        return '...' + path[-maxLength:]
    else:
        return path

mibsSeen = mibsCopied = mibsFailed = 0

mibsRevisions = {}

for srcDirectory in inputMibs:

    if verboseFlag:
        sys.stderr.write('Reading "%s"...\r\n' % srcDirectory)

    if os.path.isfile(srcDirectory):
        mibFiles = [(os.path.abspath(os.path.dirname(srcDirectory)), os.path.basename(srcDirectory))]

    else:
        mibFiles = [(os.path.abspath(dirName), mibFile)
                    for dirName, _, mibFiles in os.walk(srcDirectory)
                    for mibFile in mibFiles]

    for srcDirectory, mibFile in mibFiles:

        mibsSeen += 1

        # TODO(etingof): also check module OID to make sure there is no name collision

        try:
            mibName, srcMibRevision = getMibRevision(srcDirectory, mibFile)

        except error.PySmiError as ex:
            if verboseFlag:
                sys.stderr.write('Failed to read source MIB "%s": %s\r\n' % (os.path.join(srcDirectory, mibFile), ex))

            if not quietFlag:
                sys.stderr.write('FAILED %s\r\n' % shortenPath(os.path.join(srcDirectory, mibFile)))

            mibsFailed +=1

            continue

        if mibName in mibsRevisions:
            dstMibRevision = mibsRevisions[mibName]

        else:
            try:
                _, dstMibRevision = getMibRevision(dstDirectory, mibName)

            except error.PySmiError as ex:
                if verboseFlag:
                    sys.stderr.write('MIB "%s" is not available at the '
                                     'destination directory "%s": %s\r\n' % (os.path.join(srcDirectory, mibFile),
                                                                             dstDirectory, ex))

                dstMibRevision = datetime.fromtimestamp(0)

            mibsRevisions[mibName] = dstMibRevision

        if dstMibRevision >= srcMibRevision:
            if verboseFlag:
                sys.stderr.write('Destination MIB "%s" has the same or newer revision as the '
                                 'source MIB "%s"\r\n' % (os.path.join(dstDirectory, mibName),
                                                          os.path.join(srcDirectory, mibFile)))
            if not quietFlag:
                sys.stderr.write('NOT COPIED %s (%s)\r\n' % (
                    shortenPath(os.path.join(srcDirectory, mibFile)), mibName))

            continue

        mibsRevisions[mibName] = srcMibRevision

        if verboseFlag:
            sys.stderr.write('Copying "%s" (revision "%s") -> "%s" (revision "%s")\r\n' % (
                os.path.join(srcDirectory, mibFile), srcMibRevision,
                os.path.join(dstDirectory, mibName), dstMibRevision))

        try:
            shutil.copy(os.path.join(srcDirectory, mibFile), os.path.join(dstDirectory, mibName))

        except Exception as ex:
            if verboseFlag:
                sys.stderr.write('Failed to copy MIB "%s" -> "%s" (%s): "%s"\r\n' % (
                    os.path.join(srcDirectory, mibFile), os.path.join(dstDirectory, mibName), mibName, ex))

            if not quietFlag:
                sys.stderr.write('FAILED %s (%s)\r\n' % (
                    shortenPath(os.path.join(srcDirectory, mibFile)), mibName))

            mibsFailed += 1

        else:
            if not quietFlag:
                sys.stderr.write('COPIED %s (%s)\r\n' % (
                    shortenPath(os.path.join(srcDirectory, mibFile)), mibName))

            mibsCopied +=1

if not quietFlag:
    sys.stderr.write("MIBs seen: %d, copied: %d, failed: %d\r\n" % (mibsSeen, mibsCopied, mibsFailed))

sys.exit(EX_OK)

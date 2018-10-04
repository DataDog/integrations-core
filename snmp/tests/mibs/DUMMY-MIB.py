# flake8: noqa
# PySNMP MIB module DUMMY-MIB (http://pysnmp.sf.net)
# ASN.1 source file:///Users/hippolytehenry/Datadog/integrations-core/snmp/tests/compose/data/DUMMY-MIB.txt
# Produced by pysmi-0.2.2 at Thu Oct  4 16:55:02 2018
# On host Hippolytes-MacBook-Pro.local platform Darwin version 17.7.0 by user hippolytehenry
# Using Python version 2.7.14 (default, May 11 2018, 14:04:47) 
#
Integer, ObjectIdentifier, OctetString = mibBuilder.importSymbols("ASN1", "Integer", "ObjectIdentifier", "OctetString")
NamedValues, = mibBuilder.importSymbols("ASN1-ENUMERATION", "NamedValues")
ConstraintsUnion, SingleValueConstraint, ConstraintsIntersection, ValueSizeConstraint, ValueRangeConstraint = mibBuilder.importSymbols("ASN1-REFINEMENT", "ConstraintsUnion", "SingleValueConstraint", "ConstraintsIntersection", "ValueSizeConstraint", "ValueRangeConstraint")
NotificationGroup, ModuleCompliance = mibBuilder.importSymbols("SNMPv2-CONF", "NotificationGroup", "ModuleCompliance")
Integer32, MibScalar, MibTable, MibTableRow, MibTableColumn, NotificationType, MibIdentifier, IpAddress, TimeTicks, Counter64, Unsigned32, enterprises, iso, Gauge32, ModuleIdentity, ObjectIdentity, Bits, Counter32 = mibBuilder.importSymbols("SNMPv2-SMI", "Integer32", "MibScalar", "MibTable", "MibTableRow", "MibTableColumn", "NotificationType", "MibIdentifier", "IpAddress", "TimeTicks", "Counter64", "Unsigned32", "enterprises", "iso", "Gauge32", "ModuleIdentity", "ObjectIdentity", "Bits", "Counter32")
DisplayString, TextualConvention = mibBuilder.importSymbols("SNMPv2-TC", "DisplayString", "TextualConvention")
dummy = MibIdentifier((1, 3, 6, 1, 4, 1, 123456789))
scalar = MibScalar((1, 3, 6, 1, 4, 1, 123456789, 1), Integer32().subtype(subtypeSpec=ValueRangeConstraint(1, 65535))).setMaxAccess("readonly")
if mibBuilder.loadTexts: scalar.setStatus('mandatory')
mibBuilder.exportSymbols("DUMMY-MIB", scalar=scalar, dummy=dummy)

# Simulation data file format

## Conventions

- Simulation data for profiles is contained in [`.snmprec` files located in the tests directory](https://github.com/DataDog/integrations-core/tree/master/snmp/tests/compose/data).
- Simulation files must be named after the SNMP community string used in the profile unit tests. For example: `cisco-nexus.snmprec`.

## File contents

Each line in a `.snmprec` file corresponds to a value for an OID.

Lines must be formatted as follows:

```
<OID>|<type>|<value>
```

For the list of supported types, see the [`snmpsim` simulation data file format](http://snmplabs.com/snmpsim/managing-simulation-data.html#file-format) documentation.

!!! warning
    Due to a limitation in of `snmpsim`, contents of `.snmprec` files must be **sorted in lexicographic order**.

    Use `$ sort -V /path/to/profile.snmprec` to sort lines from the terminal.

## Symbols

For [symbol metrics](./profile-format.md#symbol-metrics), add a single line corresponding to the symbol OID. For example:

```console
1.3.6.1.4.1.232.6.2.8.1|2|1051200
```

## Tables

!!! tip
    Adding simulation data for tables can be particularly tedious. This section documents the manual process, but automatic generation is possible — see [How to generate table simulation data](./how-to.md#generate-table-simulation-data).

For [table metrics](./profile-format.md#table-metrics), add one copy of the metric per row, appending the index to the OID.

For example, to simulate 3 rows in the table `1.3.6.1.4.1.6.13` that has OIDs `1.3.6.1.4.1.6.13.1.6` and `1.3.6.1.4.1.6.13.1.8`, you could write:

```console
1.3.6.1.4.1.6.13.1.6.0|2|1051200
1.3.6.1.4.1.6.13.1.6.1|2|1446
1.3.6.1.4.1.6.13.1.6.2|2|23
1.3.6.1.4.1.6.13.1.8.0|2|165
1.3.6.1.4.1.6.13.1.8.1|2|976
1.3.6.1.4.1.6.13.1.8.2|2|0
```

!!! note
    If the table uses [table metric tags](./profile-format.md#table-metrics-tagging), you may need to add additional OID simulation data for those tags.

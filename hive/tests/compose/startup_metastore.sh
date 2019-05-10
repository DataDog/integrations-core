#!/bin/bash

/opt/hive/bin/schematool -dbType derby -initSchema

/opt/hive/bin/hive --service metastore

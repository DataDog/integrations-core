# Directory Integration

## Overview

This check monitor and report metrics on files for a set of directories.

## Installation

Ensure that the user account running the Agent (typically dd-agent) has read
access to the monitored directories and files.

## Configuration

Edit the `conf.d/directory.yaml` file.

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        directory
        -----------
          - instance #0 [OK]
          - Collected 39 metrics & 0 events

## Compatibility

The Directory check is compatible with all major platforms

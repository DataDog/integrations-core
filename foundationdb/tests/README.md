# FoundationDB E2E Setup

The FoundationDB check and E2E environment require the FoundationDB client libraries to be present on the machine. They are typically included when installing FoundationDB Server. If you run into this error: `Unable to locate the FoundationDB API shared library!"`, this means that you probably don't have the FoundationDB client libraries installed or properly configured.  

## Install Client Libraries on MacOS

Follow the official [Client-only Installation instructions][1] to install the FoundationDB client libraries. Be sure to de-select the install `FoundationDB Server` option. 

[1]: https://apple.github.io/foundationdb/getting-started-mac.html
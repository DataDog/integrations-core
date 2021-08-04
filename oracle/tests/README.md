# Instant client permissions on Mac OS

If you're getting pop up errors saying that Mac OS cannot verify the developer run the following commands
```
sudo xattr -d com.apple.quarantine  /opt/oracle/instantclient_19_8/libclntsh.dylib.19.1
sudo xattr -d com.apple.quarantine  /opt/oracle/instantclient_19_8/libnnz19.dylib
sudo xattr -d com.apple.quarantine  /opt/oracle/instantclient_19_8/libclntshcore.dylib.19.1
sudo xattr -d com.apple.quarantine  /opt/oracle/instantclient_19_8/libociicus.dylib
```

# Running docker e2e tests locally 

Before running e2e tests locally you need to `docker login container-registry.oracle.com` with valid credentials.

The credentials is the one used to login to https://container-registry.oracle.com/.

The image we are using is named `Oracle Database Enterprise Edition`.

# Test environment for SAP HANA

This integration can be tested using the Docker Compose environment.

Running the environment requires a rather large amount of memory, so make sure that Docker has a comfortable amount of RAM available - 6GB should be enough. Otherwise, spinning up the Docker Compose environment may fail with the following error:

```
Entering post start phase ...
Creating tenant database ...
* -10807: System call 'recv' failed, rc=104:Connection reset by peer {127.0.0.1:39017}
```

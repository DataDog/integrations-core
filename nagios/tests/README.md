Integration tests
=================
As this integration works by reading and tailing multiple log and config files this integration
environment only spawns one image and nagios gets installed on it.
At this moment no shared volume has been configured so the integration test does nothing

To check the integration start the environment, log in the docker and run:
```
agent check nagios --pause 60000 --check-times 2
```

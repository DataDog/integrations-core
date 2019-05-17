Run integration tests
=====================
Nagios integration reads local files from the host. e2e tests assume that all communication
between agent and host is done through a port, which is not the case, so basically we need
to install nagios on the agent machine.

To do so run install_nagios script in the agent machine and then run the agent check
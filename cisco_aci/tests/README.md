## How to test cisco_aci

It is not possible to test this integration with a simple `docker compose` environment on which to run the agent. This document lists some of the available options to test this integration. Note that installing a real cisco ACI environment is not feasible as it requires a custom hardware setup.

### Unit tests

The integration is tested thanks to unit tests mocking the API responses extensively. Those units tests should
continue to be as extensive as possible as only those are run in the CI for every PR.

### Cisco Application Centric Infrastructure Simulator

Cisco has created VM images for a simulator that is said to behave exactly like a real cisco ACI setup. However, these images are only offered under a partnership contract.

### Cisco public sandbox

https://devnetsandbox.cisco.com/

Even if the simulator cannot be installed on a VM, cisco offers a publicly available sandbox which is running a specific version
of the simulator. This AlwaysOn simulator is very convenient to use as it doesn't require a VPN.

To use it, create an account using the link, and start the ACI Simulator AlwaysOn sandbox. Configure a locally-running Agent to point at the sandbox with the following configuration:

```yaml
instances:
  - aci_url: https://sandboxapicdc.cisco.com
    username: admin
    pwd: <PASSWORD>
```

Make sure to replace the `<PASSWORD>` with the password it gives for the ACI Sandbox.

Alternatively, add a temporary `conftest.py` with the following contents:

```python
import pytest

SANDBOX_CONFIG = {
    'instances': [
        {
            'aci_url': 'https://sandboxapicdc.cisco.com',
            'username': 'admin',
            'pwd': '<PASSWORD>',
            'tls_verify': False,  # As of 2019-12-03, the sandbox endpoint doesn't have a valid TLS certificate.
        }
    ]
}


@pytest.fixture(scope="session")
def dd_environment():
    return SANDBOX_CONFIG
```

and use `ddev` to run the check. (Be sure not to commit this `conftest.py`, as we should only use the sandbox for manual testing.)

The main downsides of this are that:
- Anyone can modify the environment and thus tests cannot be reproducible.
- Only one version of the cisco API is provided 3.0(2k) as of 07/08/19.

Yet this is a very convenient way to test the integration against a real system.

### Other sandboxes

Cisco also provides private sandboxes using either the previous simulator or a lab one on real hardware, and one with their
kubernetes integration installed.

The major downsides here are:
- Only one version of the cisco api.
- The sandbox comes with almost nothing configured and you have to setup the whole environment otherwise most metrics won't show up.
- Such a sandbox requires you to reserve it, sometimes one day in advance.
- It requires the use of a VPN that may be incompatible with other corporate VPNs.

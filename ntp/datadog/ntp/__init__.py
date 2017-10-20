from .ntp import NtpCheck

def main():
    check = NtpCheck(name='ntp', init_config=None, agentConfig={})
    check.check({})

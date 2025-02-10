from checks import AgentCheck


class HelloCheck(AgentCheck):
    def check(self, instance):
        from cryptography.exceptions import InternalError
        from cryptography.hazmat.primitives import hashes

        try:
            hashes.Hash(hashes.MD5())
        except InternalError:
            self.gauge('cryptography_status', 0)
        else:
            self.gauge('cryptography_status', 1)

        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        try:
            ctx.set_ciphers("MD5")
        except ssl.SSLError as e:
            self.gauge('ssl_status', 0)
            self.log.warn(f"Exception: {e}")
        else:
            self.gauge('ssl_status', 1)

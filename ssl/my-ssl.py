import socket
import ssl

hostname = 'google.com'
context = ssl.create_default_context()

with socket.create_connection((hostname, 443)) as sock:
    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
        print(ssock.getpeercert())
        print(ssock.version())

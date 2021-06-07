from typing import AnyStr, Any, Dict
import random
import string

USERS = {
    "user1": "dummy_pass"
}


class MockedAviClientSession(object):
    def __init__(self):
        self._user_sessions = {}
        self._user_csrf = {}
        self.cookies = {}

    def post(self, url: AnyStr, *args: Any, **kwargs: Any):
        if not url.endswith("/login"):
            raise Exception(f"[MockedAviClient] Invalid post url: {url}")

        headers = kwargs['headers']
        user, password = headers['username'], headers['password']
        if user in USERS and USERS[user] == password:
            # Successful auth
            csrf_token = ''.join(random.choice(string.printable) for _ in range(30))
            session_id = ''.join(random.choice(string.printable) for _ in range(30))
            self._user_csrf[user] = csrf_token
            self._user_sessions[user] = session_id

    def get(self, url: AnyStr):







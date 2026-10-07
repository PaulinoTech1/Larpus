"""Single-owner authentication; secrets and limits never leave this process."""
import getpass
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import deque
from http.cookies import SimpleCookie
from runtime.agents import ROOT

PASSWORD_FILE = ROOT / 'data/password.json'
FAILURE = "You're Larping already"

def password_record(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 256:
        raise ValueError('Use a password of 12–256 characters')
    salt = secrets.token_bytes(32)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return {'salt':salt.hex(), 'hash':digest.hex()}

class Auth:
    def __init__(self, record):
        self.salt = bytes.fromhex(record['salt'])
        self.digest = bytes.fromhex(record['hash'])
        if len(self.salt) != 32 or len(self.digest) != 64:
            raise ValueError('Invalid password record')
        self.sessions = {}
        self.windows = {}
        self.lock = threading.RLock()

    def allowed(self, key, limit, period):
        with self.lock:
            now = time.monotonic()
            for old in list(self.windows):
                if self.windows[old][0] <= now:
                    del self.windows[old]
            if key not in self.windows:
                if len(self.windows) >= 2048:
                    return False
                self.windows[key] = (now + period, 0)
            deadline, count = self.windows[key]
            if count >= limit:
                return False
            self.windows[key] = (deadline, count + 1)
            return True

    def login(self, ip, password):
        # Count every attempt, even valid ones. Global cap prevents IP rotation.
        with self.lock:
            if not self.allowed(('login',ip),5,60) or not self.allowed(('login-global',),20,60):
                return 429, None
            if not isinstance(password,str) or not 1 <= len(password) <= 256:
                return 401, None
            digest = hashlib.scrypt(password.encode(),salt=self.salt,n=16384,r=8,p=1)
            if not hmac.compare_digest(digest,self.digest):
                return 401, None
            self.prune()
            if len(self.sessions) >= 128:
                return 429, None
            token = secrets.token_urlsafe(32)
            self.sessions[hashlib.sha256(token.encode()).digest()] = time.monotonic()+8*3600
            return 200, token

    def prune(self):
        now=time.monotonic()
        self.sessions={key:expiry for key,expiry in self.sessions.items() if expiry>now}

    def session(self, header):
        try:
            cookie=SimpleCookie();cookie.load(header or '')
            token=cookie['larpus_session'].value
            if len(token)>100:
                return None
            key=hashlib.sha256(token.encode()).digest()
        except (KeyError, ValueError):
            return None
        with self.lock:
            self.prune()
            return key if key in self.sessions else None

    def logout(self,key):
        with self.lock:
            self.sessions.pop(key,None)

def main():
    password=getpass.getpass('New Larpus password (12–256 characters): ')
    if password!=getpass.getpass('Confirm password: '):
        raise ValueError('Passwords do not match')
    record=password_record(password)
    PASSWORD_FILE.parent.mkdir(exist_ok=True)
    temp=PASSWORD_FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(record),encoding='utf-8')
    temp.replace(PASSWORD_FILE)
    print('Password stored as a salted scrypt hash. Restart Larpus to apply.')

if __name__=='__main__':
    main()

# Password gate and rate limits

Set/reset the password locally: `python -m runtime.auth`. The hidden prompt asks
twice; use 12–256 characters. Only a random salt and scrypt hash (N=16384,r=8,p=1)
are saved in ignored `data/password.json`. Restrict that file to the owner's OS
account; anyone able to replace it can reset access. Restart both gateway
processes after changing it. Startup fails closed if the file is missing/invalid.
`scripts/start-lan.ps1` offers this prompt automatically on first setup.

Unauthenticated page requests go to `/login`; APIs require an authenticated
session. Every failed login returns “You're Larping already”. Limits:
- 5 login attempts per source IP per 60-second fixed window.
- 20 login attempts globally per 60-second fixed window.
- 30 authenticated API POSTs per source IP per 60-second fixed window.
- Rate-limited responses use HTTP 429 and `Retry-After: 60`.

Limits count valid and invalid login attempts before hashing. Client IP is taken
from the socket, never forwarded headers. Limits and sessions are host-process
memory and reset on restart; separate loopback/LAN processes do not share limits.
Eight-hour sessions use random 256-bit opaque tokens, with only token hashes
stored in memory, HttpOnly/SameSite=Strict cookies, no browser storage. Lock
Station invalidates the current session. Restart invalidates every session.
Cookie authentication does not bypass Host/Origin or LAN subnet checks.

Current LAN HTTP does not encrypt passwords or session cookies; Secure cookies
require HTTPS and cannot be used on this HTTP URL. This is an access gate for a
trusted home LAN, not protection from network monitoring. Local HTTPS is the next
step for encrypted access. No external services are introduced.

Guidance: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

# Local HTTP and LAN HTTPS

Start with scripts/start-lan.ps1. Local HTTP requires no password; the existing password protects LAN HTTPS:
http://127.0.0.1:8080 (loopback only) and https://192.168.1.2:8080 (home LAN).
LAN plaintext HTTP is no longer served. TLS requires the existing certificate
and key; missing credentials stop startup without falling back to LAN HTTP.
Session cookies use Secure on HTTPS. Origin checks follow the listener scheme.

Certificates are generated locally with scripts/create-local-tls.py after creating
data/tls and protecting it using scripts/protect-quarantine.ps1. Existing keys
are preserved. The LAN certificate includes the configured IP and expires after
one year; the local CA lasts ten years. Changing the LAN IP requires a new matching
server certificate. Inspect existing credentials before renewal; do not overwrite
the CA without planning to update client trust.

The station's current Windows user trusts the CA. On each other LAN client,
transfer only data/tls/ca.crt and import it as a trusted root for that device/browser.
Do not transfer ca.key or server.key. Private keys remain in the ignored,
owner/SYSTEM-only data/tls directory and are never mounted into the model pod.
Public certificate trust on another device and its authenticated session still
require testing there. The firewall port remains 8080, scoped to the home subnet.

The local HTTP listener is intentionally unencrypted and requires no password.
Only the loopback listener and loopback clients receive this bypass; local
processes can use it. The LAN listener always requires authentication.
No cloud certificate service, account or external CA is used.

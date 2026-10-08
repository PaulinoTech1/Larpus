# Home LAN access

Start/check the isolated backend, then run scripts/start-lan.ps1.
Local: http://127.0.0.1:8080 without password.
LAN: https://192.168.1.2:8080 with password and home-subnet checks.
Plaintext LAN HTTP is rejected. See [HTTPS](HTTPS.md) for public CA trust.

The elevated scripts/enable-lan-firewall.ps1 scopes TCP 8080 to Python, Wi-Fi 2,
192.168.1.2 and 192.168.1.0/24. Previous creation was denied without elevation;
second-device connectivity remains unverified. Do not enable router forwarding,
UPnP or public tunnels. Reserve the address in DHCP; changes require updated
launch/firewall settings and a matching certificate. No autostart is installed.

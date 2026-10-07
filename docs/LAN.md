# Home LAN access

Run `scripts/start-lan.ps1` to serve the HUD on `http://192.168.1.2:8080`.
It binds only the Wi-Fi address and accepts clients from `192.168.1.0/24`.
Host/Origin checks include the configured address. Ollama stays on loopback.

Run `scripts/enable-lan-firewall.ps1` once in Administrator PowerShell. It allows
TCP 8080 only for Python, local address 192.168.1.2, interface Wi-Fi 2, and remote
subnet 192.168.1.0/24. The current Public network profile is left unchanged.
Undo as Administrator: `Remove-NetFirewallRule -Name Larpus-Home-LAN`.

From a phone/computer on home Wi-Fi, open the same URL. Guest Wi-Fi or client
isolation can block access. Reserve the PC address in DHCP; if it changes, update
both scripts. No router port forwarding, UPnP mapping, or public tunnel is needed.

Devices on this trusted subnet can use chat without authentication. This remains
a development server without TLS. Subnet checks cannot identify a router proxy
or tunnel presenting remote traffic as a local client; keep forwarding/tunnels
disabled. Future microphone capture needs HTTPS on LAN; current voice is a stub.

Default gateway startup stays loopback-only. LAN settings are `LARPUS_HOST` and
`LARPUS_LAN_CIDR`; remove them from the shell and stop the LAN process to revert.
No scheduled startup is installed. Scripts default to this PC's current LAN.

Verification: LAN URL returned HTTP 200 from this PC; client-subnet and origin
tests pass. Firewall creation was denied (Windows error 5); an Administrator must
run the supplied rule script. Connectivity from another device remains untested.

---
query: Tailscale Serve private HTTPS owner identity headers CLI grants
date: 2026-10-10
ttl: 30
---
Official references reviewed:
- https://tailscale.com/docs/features/tailscale-serve
- https://tailscale.com/docs/reference/tailscale-cli/serve
- https://tailscale.com/docs/reference/syntax/grants
Serve is tailnet-only; Funnel is public. Serve inserts Tailscale-User-Login and
removes incoming spoofed versions. Tagged nodes do not receive user headers.
Bind the target service to localhost to constrain header spoofing to local actors.
Foreground Serve defaults to HTTPS and stops with session; --bg persists/restarts.
`tailscale serve --https=443 http://127.0.0.1:8088` proxies a loopback HTTP bridge.
Disable the same route with `tailscale serve --https=443 off`; avoid global reset.
Grants support host CIDRs and tcp:443; overlapping ACL/grant permissions are additive.
Verified integration locally against the existing gateway; actual Serve and Pixel
acceptance remain pending installation/account login and owner policy review.

# Mobile access through self-hosted Headscale (design, not implemented)

Status: **design only, 2026-10-15. Nothing in this document has been executed.**
Every step in the implementation plan needs explicit owner approval first. No
code, script, firewall rule, router setting or container in this repo changes
with this document. See the [decision record](DECISIONS.md) entry of the same date.

Goal: the owner reaches LARPUS from his Google Pixel, from anywhere, through a
self-hosted [Headscale](https://github.com/juanfont/headscale) control server and the
stock open-source Tailscale Android client. Nothing in the path may rely on a
cloud service, account, telemetry or remote asset.

Hard constraints (owner decision 2026-10-15):

- No Tailscale SaaS control plane and no Tailscale account.
- No Tailscale-hosted DERP relays. Headscale's embedded DERP is enabled, and the
  default DERP map is removed (`derp.urls: []`).
- No third-party IdP (Google, Microsoft, GitHub and others). Optional OIDC is self-hosted only.
- No cloud DNS, no cloud certificate service and no public tunnel service.
- **No port forwarding on the home router of any kind** (no 443, no 3478, no UPnP/NAT-PMP).
  The home PC makes **outbound connections only**. Inbound IPv6 to the home is
  excluded for the same reason: an IPv6 firewall pinhole exposes a port just as a forward does.
- The existing LARPUS password, sessions and rate limits stay in force. The
  tailnet is an extra layer, not a replacement.

Relation to [TAILSCALE_DEMO.md](TAILSCALE_DEMO.md): that demo used the Tailscale
coordination service and Tailscale Serve. This design is meant to replace it
for ongoing phone access. It does not delete the demo document or its bridge.

## 1. Threat model

Assets: conversations, notes, the quarantine volume and corpus, the LARPUS
password hash, the TLS CA key, the Headscale private keys and node database, and the owner's
location/usage metadata.

| Adversary / failure | In scope | Mitigation |
|---|---|---|
| Internet scanners | yes | Nothing at home listens on WAN (no forwards, no IPv6 pinholes). In option R-A, only the off-site Headscale/DERP host is exposed. It holds no LARPUS data and is kept patched and pinned. |
| Off-site host operator (VPS provider) | yes (R-A) | It is third-party infrastructure. It can see metadata (node IPs, timing, the tailnet map) and could tamper with control (add nodes, change ACLs), but not read WireGuard payloads. Mitigations: full-disk encryption where the provider allows, no LARPUS data or CA keys stored there, the LARPUS password still required, and the ACL/node list audited from the owner side. |
| Stolen or lost Pixel | yes | Revoke the node in Headscale (section 10). The LARPUS password and 8-hour sessions still apply. The Android screen lock is required. |
| Rogue node joining the tailnet | yes | No open registration. Single-use, short-lived pre-auth keys or explicit `headscale nodes register` approval. The ACL admits only the Pixel. |
| Compromised Headscale container | yes | The container runs in its own rootless pod, has no LARPUS volumes, and lives in a different namespace from the offline pod. Traffic is end-to-end WireGuard, so the control server cannot read it. It *can* add nodes and rewrite ACLs, so the LARPUS password remains a required second gate. |
| Malicious relay / on-path ISP | yes | WireGuard encrypts traffic end to end. DERP relays only ciphertext, and the relay is our own. |
| Metadata leak to Tailscale Inc. (logtail, DERP map, control) | yes | Custom control URL, `derp.urls: []`, and client log upload disabled where possible (open question Q3). |
| Password guessing / credential stuffing via the phone path | yes | MFA (section 16.1), per-identity and per-IP login buckets, exponential temporary bans (16.2, 16.3) |
| Stolen session cookie | yes | Secure/HttpOnly/SameSite=Strict, short sessions, MFA step-up for sensitive actions, binding the session to the node identity (16.3, 16.4) |
| GPU exhaustion / inference DoS by a valid but abusive client | yes | Global inference concurrency cap and per-session chat buckets (16.3) |
| Off-site host brute force (R-A) | yes | Host firewall allows only Headscale/DERP, key-only SSH from the tailnet, auto-ban (16.2) |
| Owner's own PC compromised | no | Same trusted-machine boundary as [AUTH.md](AUTH.md). |
| Nation-state / targeted Android exploit | no | Out of scope for a single-owner home station. |
| Availability (home power, ISP, off-site host) | accepted risk | Single DERP and single control server are single points of failure ([Headscale DERP docs](https://headscale.net/stable/ref/derp/)). LAN access remains the fallback. |

## 2. Architecture

Placement depends on the reachability choice (section 8). In both cases the home PC
only dials out.

```text
R-A (off-site):
Pixel (Tailscale app) --HTTPS/Noise, STUN, DERP--> off-site host: headscale + embedded DERP
                                                         ^ outbound only
PC tailnet node (tailscaled) -----------------------------+
Pixel <== WireGuard (direct via NAT traversal, or relayed as ciphertext by DERP) ==> PC node
PC node --tailnet only--> LARPUS gateway (password, TLS) -> larpus-offline pod (unchanged)

R-B (LAN-only):
Pixel on home Wi-Fi --LAN--> larpus-headscale pod on the PC (no WAN exposure)
Pixel <== WireGuard over LAN ==> PC node --> LARPUS gateway
```

Rules:

- Wherever Headscale runs, it runs as a separate rootless Podman pod
  (`larpus-headscale`) with its own network namespace. It never joins `larpus-offline`, and it mounts no
  LARPUS data, quarantine, `data/tls` CA key or Podman socket. It runs with a read-only root,
  a tmpfs at `/var/run/headscale`, dropped capabilities and no-new-privileges, following
  [WINDOWS-HOME-ISOLATION.md](WINDOWS-HOME-ISOLATION.md) and the upstream
  [container guide](https://headscale.net/stable/setup/install/container/).
- Its only persistent state is `config/` (read-only) and `lib/` (the SQLite DB,
  Noise private key and DERP private key) in a dedicated volume.
- Port clash, which applies on the PC in R-B: Headscale's default `listen_addr` is `:8080`,
  the same port as the LARPUS gateway. Use a different port. The metrics (`:9090`) and gRPC
  listeners stay on loopback and are never published.
- The offline LARPUS pod and the `runtime.isolation` checks are untouched.

## 3. PC node: how the PC joins the tailnet

The LARPUS gateway (`python -m runtime.gateway`) runs on **Windows**, not
inside WSL ([DEPLOYMENT.md](DEPLOYMENT.md), `scripts/run-isolated.ps1`). That is the
main design constraint, because a tailnet IP that lives inside WSL is not a
Windows interface the gateway can bind to.

Options:

A. **tailscaled in a dedicated rootless container** in its own pod (for example
   `larpus-tailnode`), using userspace networking (`--tun=userspace-networking`).
   This needs no `/dev/net/tun` and no root, and stays separate from Headscale and
   the offline pod. It forwards one tailnet port to the gateway. Caveat: traffic arrives at
   the Windows gateway from the WSL virtual NIC, not from 192.168.1.0/24, so the
   gateway's LAN-subnet check would reject it. Making it work requires either a
   code change, so the gateway gets a third, tailnet-scoped listener (out of scope here),
   or forwarding to a loopback bridge like the demo's `tailscale_bridge.py`.
   This needs a WSL networking decision (Q1).
B. **tailscaled directly in the Larpus WSL distro.** The same Windows-vs-WSL
   interface problem applies, and it adds a root daemon to the isolation distro,
   which this design does not recommend.
C. **Tailscale Windows client with `tailscale login --login-server=<URL>`**
   ([custom control server KB](https://tailscale.com/kb/1507/custom-control-server)).
   The tailnet IP becomes a real Windows interface, so the gateway could bind to it.
   This deviates from "tailscaled in WSL or a container" and is listed for the owner's consideration only.

WSL2 caveats on Windows 11 Home:

- The PC node only makes outbound connections (to the off-site control/DERP in R-A),
  so in R-A it works in default NAT mode with no inbound rules.
- In R-B, Headscale on the PC must be reachable from the LAN. In NAT mode that needs a
  Windows `netsh interface portproxy` rule, which is TCP only, so it cannot carry STUN on UDP 3478.
  STUN/DERP are largely unnecessary on a single LAN, but direct WireGuard
  between the phone and a node inside NAT-mode WSL may still fail and fall back to relay.
- Mirrored networking mode (`networkingMode=mirrored` in `.wslconfig`) shares the host's
  interfaces with WSL and supports UDP. It is a per-user WSL setting, not a
  Pro-only feature, but it changes networking for **every** WSL distro on the
  machine, including docker-desktop. It also needs the Hyper-V firewall rules for WSL to allow
  the ports. See the [WSL networking docs](https://learn.microsoft.com/en-us/windows/wsl/networking).
  This is an owner decision (Q1).
- WSL shuts down idle distros. Headscale only runs while the Larpus distro is
  running. No autostart is installed today, and this design does not add one.
- The Windows firewall is configured per port and per profile. Any new rule must be scoped
  as tightly as the existing [LAN.md](LAN.md) rule, and needs an elevated prompt.

## 4. Gateway binding

- The gateway **never** binds to `0.0.0.0` and is **never** reachable from WAN.
  No router forward ever points at port 8080.
- Allowed: (a) bind an additional listener only to the PC's tailnet IP
  (100.64.0.0/10 range, IP assigned by Headscale), *or* (b) keep the gateway on
  loopback/LAN and have the tailnet node forward into it, the same pattern as
  the demo bridge, which never targets the password-free `127.0.0.1:8080` listener.
- The password-free local HTTP listener must stay reachable only from loopback. A
  forwarder must target the authenticated HTTPS listener, so tailnet requests
  always hit the password gate.
- Any listener change is a code change and needs its own PR and tests.

## 5. Headscale policy (ACL) for the Pixel only

Headscale with no policy file **allows all traffic**, and a policy without
`acls`/`grants` also allows all ([policy docs](https://headscale.net/stable/ref/acls/)).
So a policy file is mandatory. Grants are the recommended form. Sketch, with
users and tags to be fixed at implementation:

The authoritative policy file is in [section 15](#15-zero-trust-networking-nist-sp-800-207).
In short: the Pixel is tagged `tag:pixel`, the PC node is tagged `tag:larpus`, and one
grant allows `tag:pixel` to reach `tag:larpus` on the gateway port only.

- The PC node is tagged `tag:larpus` and the Pixel `tag:pixel`. Any other node, including
  an untagged owner device, matches no grant and reaches nothing.
- No exit nodes, subnet routes, Tailscale SSH or Taildrive.
- After each reload, check that `headscale` logs a successful policy load. A
  rejected policy must not leave a stale filter. This was fixed in v0.29.5
  ([release notes](https://github.com/juanfont/headscale/releases/tag/v0.29.5)).

## 6. TLS for Headscale

The phone must reach Headscale over HTTPS. Headscale accepts a supplied
`tls_cert_path`/`tls_key_path`. **The certificate must include the full chain or
the Tailscale Android client rejects it** ([TLS docs](https://headscale.net/stable/ref/tls/)).
Headscale's built-in Let's Encrypt/ACME is **not** used, because it relies on an external CA service.

Plan: issue a Headscale server certificate from the project's existing local CA
(`scripts/create-local-tls.py` pattern, [HTTPS.md](HTTPS.md)), or from a separate
dedicated CA. The SAN must match `server_url` (a hostname from section 8 or a raw IP).
Serve the full chain (leaf plus CA). The CA private key never enters the Headscale pod.
Only the leaf key and chain go in.

Android CA-trust caveats:

- A CA imported by the user goes in the *user* store. Since Android 7, apps
  trust user CAs only if their Network Security Config opts in
  ([Android docs](https://developer.android.com/privacy-and-security/security-config)).
  Chrome trusts user CAs, so the LARPUS web UI should work. Whether the
  **Tailscale Android app** trusts user-added CAs for its control connection is
  **not confirmed** (Q2). If it does not, the options are a CA it trusts (none without a public
  CA) or an IP-pinned approach, and this could block the design. This must be tested on the Pixel before any WAN exposure.
- Reusing the LARPUS CA means a Headscale-key compromise can't mint certs. But
  the CA is broadly trusted on the owner's devices, so a separate, name-constrained CA
  limits blast radius (Q6).
- Track leaf expiry. Use one year to match HTTPS.md.

## 7. Optional self-hosted OIDC (extra layer)

Headscale supports OIDC with PKCE and `allowed_users` filtering, and lists both
Authelia and Authentik as fully supported
([Headscale OIDC docs](https://headscale.net/stable/ref/oidc/)).

| | Authelia | Authentik |
|---|---|---|
| Footprint | Single Go binary/container; file or SQLite backends | Server and worker plus PostgreSQL; at least 2 CPU / 2 GB RAM ([install docs](https://docs.goauthentik.io/install-config/install/docker-compose/)) |
| Headscale guide | [Official integration page](https://www.authelia.com/integration/openid-connect/clients/headscale/) (tested Authelia v4.39.28 / Headscale v0.29.1) | [Authentik's Headscale integration](https://integrations.goauthentik.io/networking/headscale/) |
| Attack surface | Small; config-as-file | Large admin UI; the default compose mounts the Docker socket into the worker (must be removed) |
| Telemetry | Verify and disable (Q5) | Error reporting is opt-in; verify other phone-home (Q5) |

**Recommendation: Authelia**, if OIDC is wanted at all. It is the smaller and
file-configured option, and it needs no database server. Use a file user backend, TOTP or
WebAuthn second factor, `require_pkce: true`, S256, and `allowed_users` set to the owner only.
Note that Authelia also needs its own HTTPS endpoint reachable by the phone during login,
which adds exposure. Headscale also offers `only_start_if_oidc_is_available`.
Weigh this against the default: single-use pre-auth keys with no IdP at
all, which is simpler and has less exposed surface. The owner decides (D2).

## 8. Reachability options (no home port forwarding)

Owner constraint (2026-10-15): **no port forwarding on the home router of any kind**
(no 443, no 3478, no UPnP), and the home PC makes outbound connections only. Inbound
IPv6 to the home is excluded too, because opening an IPv6 firewall pinhole is the same
port exposure. The earlier "home router forward" option is **dropped**.

| Option | What | Pros | Cons |
|---|---|---|---|
| **R-A. Off-site owner-controlled host** | Headscale and embedded DERP on a small host the owner controls off-site: a rented VPS, or owner hardware at a trusted location (for example a family member's home). It exposes 443/tcp and 3478/udp on *that* host only. The PC and phone dial out to it | Works on cellular from anywhere; nothing at home listens on WAN; DERP gives a relay path through any NAT/CGNAT | **A rented VPS is third-party infrastructure**, a cloud provider in practice, which bends the "no cloud" principle. The provider sees metadata (IPs, timing, node list) and controls the hypervisor, so it could tamper with the control plane. Mitigations: WireGuard encryption end to end (the relay forwards only ciphertext), full-disk encryption where possible, no LARPUS data, password or CA key stored there, pinned images, and the LARPUS password still required. Costs money and upkeep. Hardware at a trusted location avoids the provider but relies on that site's network, which would itself need a forward there |
| **R-B. LAN-only** | Headscale on the PC (or tailnet not used at all); the phone connects only on home Wi-Fi | **Zero external infrastructure**; fully consistent with local-first; nothing exposed beyond the LAN; simplest | No access away from home. Adds little over the existing LAN HTTPS + password ([LAN.md](LAN.md)) beyond WireGuard encryption and an ACL |

**Recommendation: R-B (LAN-only) now**, because it is the only option that satisfies every
principle without third-party infrastructure. Treat R-A as a later, explicit owner
opt-in if away-from-home access is worth a third-party host. If chosen, prefer
owner hardware at a trusted location over a rented VPS. This is owner decision D1.

DNS for R-A (no cloud DNS): use the host's raw IP in `server_url` with an IP SAN, which
is simplest. A VPS usually has a static IP, so the dynamic-IP problem mostly
disappears. For hardware at a trusted site with a dynamic IP, run self-managed DDNS
on owner hardware, meaning an owner-run authoritative server for a registered domain.
Hosted DNS/DDNS providers are not recommended.

## 9. Pinned versions (fill in at implementation)

| Component | Version | Image digest / checksum |
|---|---|---|
| Headscale | `v0.29.5` latest at writing ([release](https://github.com/juanfont/headscale/releases/tag/v0.29.5)); re-check | `ghcr.io/juanfont/headscale@sha256:<TBD>` |
| Tailscale Android (Play or [F-Droid](https://f-droid.org/packages/com.tailscale.ipn/)) | `<TBD>` | APK signature `<TBD>` |
| tailscaled for the PC node | `<TBD>` | `<TBD>` |
| Authelia (if approved) | `<TBD>` | `<TBD>` |

The same rule as deploy.sh applies: floating tags are refused, images are cached and exported, and
digests are recorded in the deployment manifest.

## 10. Phone side

Install the official Tailscale app (Play or F-Droid). Go to Settings, then Accounts, then the
menu, then **Use an alternate server**, and enter the Headscale URL
([Headscale Android guide](https://headscale.net/stable/usage/connect/android/),
[Tailscale KB 1507](https://tailscale.com/kb/1507/custom-control-server)).
Register either through web auth (an owner approves it in Headscale, or through OIDC) or with
**Use an auth key** and a single-use pre-auth key. Then open the LARPUS URL in
Chrome and log in with the existing password. Import the CA as described in section 6.

## 11. Key expiry and revocation

- `node.expiry`: set to a finite value (proposal: 30d). Re-auth is then needed periodically.
- Pre-auth keys: single-use, expiring within one hour, never reusable or ephemeral for the phone.
- Lost phone: `headscale nodes expire -i <id>`, then `headscale nodes delete -i <id>`.
  Rotate the LARPUS password with `python -m runtime.auth` and restart the gateway to
  invalidate sessions.
- Compromised Headscale: stop the pod (section 13), rotate the Noise and DERP private keys
  by deleting them from `lib/`, which forces every node to re-register, then reissue the TLS leaf.
- Clients may keep a working peer path after the control server goes down.
  Expiry and ACL changes need the control server to be up.

## 12. Logging, local only

- Headscale logs go to the container's stdout, kept in local journald/podman storage with
  bounded size, or are disabled like the other pods. No log drain or remote collector.
- Set `logtail.enabled: false` in Headscale. Release v0.29.5 fixed clients uploading logs
  to Tailscale Inc. despite this setting
  ([release notes](https://github.com/juanfont/headscale/releases/tag/v0.29.5)). That is one reason to pin v0.29.5 or later.
  Whether the Android app sends any other telemetry is Q3.
- Do not enable DNS options that refer to external resolvers (NextDNS and similar). Keep MagicDNS/DNS
  config minimal or off. The phone uses the tailnet IP or a hostname in the cert.
- Metrics stay on loopback inside the pod.

## 13. Rollback / kill switch

In increasing severity:

1. Phone: toggle Tailscale off, or log out.
2. `podman pod stop larpus-headscale`. Remote access ends immediately, and
   LAN/local LARPUS keep working.
3. Remove the Windows firewall/portproxy rules (R-B), or stop/destroy the off-site host (R-A). Revert
   `.wslconfig` if mirrored mode was enabled, followed by `wsl --shutdown`, which affects all distros.
4. Stop or remove the PC tailnet node or container. Delete the tailnet-only gateway
   listener if one was added.
5. Delete the pod and volume. Nothing in `larpus-offline` depends on it.

Each step is independent of the frozen release pointer and needs no reseal.

## 14. Implementation plan (NOT executed, requires owner approval per step)

0. The owner decides D1 (reachability: R-B LAN-only recommended, or R-A off-site), D4 (shorter session lifetime), D2 (OIDC yes/no, Authelia), Q1 (WSL
   networking) and Option A/B/C for the PC node (section 3).
1. **Phone CA test first (offline)**: a throwaway Headscale on the LAN only, with a cert from
   the chosen CA. Check whether the Tailscale Android app accepts it (Q2). Stop here if it does not.
2. Online preparation window: pull the Headscale (and Authelia) images by digest,
   verify checksums, export OCI archives, and record them in the manifest.
3. Create the `larpus-headscale` rootless pod: hardened flags, its own volume, config
   on the chosen host (`server_url`, `listen_addr` not 8080 on the PC, `derp.server.enabled: true`,
   `derp.urls: []`, `logtail.enabled: false`, a finite `node.expiry`, `policy.path`).
4. Write the deny-by-default policy (section 5). Reload and confirm it loaded.
5. Issue the Headscale TLS leaf with its full chain.
6. Join the PC node (chosen option) using a single-use key, and tag it `tag:larpus`.
7. Gateway exposure through the chosen section 4 approach. This needs a separate code PR with tests if a listener changes.
8. LAN-only test from the Pixel on home Wi-Fi: register, apply the ACL, and confirm that
   `tailscale debug derp-map` shows only the embedded region.
9. R-A only, if approved: provision the off-site host (FDE where possible), open 443/tcp
   and 3478/udp on that host only, and migrate or re-register nodes. **No home router forward
   and no home IPv6 pinhole, at any step.**
10. Acceptance (cellular for R-A; Wi-Fi for R-B): direct and DERP paths, password gate, ACL denial from
    a second device, revocation drill and the kill switch drill.
11. Update STATUS.md, LAN.md and DECISIONS.md with the actual results.

**Hardening code PRs (section 16), each a separate PR with tests, each needing owner approval
before merge and before activation as a release:**

- **H1 Transport and headers:** TLS 1.3 only, HSTS (hostname origin), CSP tightening,
  extra security headers and the `__Host-` cookie. Short idle/absolute sessions (D4).
- **H2 Audit log and local alerts:** append-only auth audit log, Windows toast watcher.
- **H3 Rate limits and bans:** separate login/MFA/chat buckets, per-session keys,
  persistent exponential bans, and the CSRF token plus mandatory Origin.
- **H4 MFA:** TOTP, hashed recovery codes and lockout first (works on the existing origin),
  then WebAuthn once the hostname and trusted TLS exist (blocked on Q2/Q6/Q12). Step-up
  for sensitive actions. Local-only enrollment.
- **H5 Tailnet listener and identity:** a tailnet-only bind (lifting the RFC1918-only startup check
  for the 100.64.0.0/10 address only), the Pixel-IP allowlist, and either option C or the trusted-forwarder
  identity header. Remote kill switch.
- **H6 Infrastructure (no repo code):** Windows Firewall rule and nftables in the forwarder pod;
  for R-A, off-site host firewall, SSH and fail2ban. Each runs only after explicit approval.

## 15. Zero Trust Networking (NIST SP 800-207)

This section maps the design to the seven zero-trust tenets in
[NIST SP 800-207, *Zero Trust Architecture*, section 2.1](https://doi.org/10.6028/NIST.SP.800-207)
([CSRC page](https://csrc.nist.gov/pubs/sp/800/207/final)). SP 800-207's premise is
that no implicit trust is granted based on network location or ownership, and that
subject and device authentication happen before any session to a resource. In this design,
being on the tailnet, on the LAN or on the owner's own phone is **never** enough on its own.

### Controls

1. **Per-node WireGuard key identity.** Every node has its own WireGuard key pair, plus a node
   key registered in Headscale. Packets are accepted only from a peer whose public
   key the control plane has distributed. Identity is the key, not the IP or the network.
2. **Tailnet membership grants no implicit trust.** Joining the tailnet gives a node
   an address, not access. The policy is default-deny. A node that matches no grant
   reaches nothing, and LARPUS still requires its password.
3. **Default-deny Headscale policy.** Headscale with no policy, or with a policy lacking
   `grants`/`acls`, allows everything ([Headscale policy docs](https://headscale.net/stable/ref/acls/)),
   so this file is mandatory and checked after every reload:

   ```jsonc
   // /etc/headscale/policy.json  (policy.path in config.yaml)
   {
     "tagOwners": {
       "tag:pixel":  ["owner@"],   // the owner's Google Pixel, the only client
       "tag:larpus": ["owner@"]    // the PC node that fronts the LARPUS gateway
     },
     "grants": [
       {
         "src": ["tag:pixel"],
         "dst": ["tag:larpus"],
         "ip":  ["tcp:<GATEWAY_TAILNET_PORT>"]   // the gateway port only, e.g. tcp:8080
       }
     ],
     // No "ssh" section: Tailscale SSH denied.
     // No "autoApprovers": no subnet routes and no exit node can be approved automatically,
     //   and none are approved manually. The PC node does not advertise any.
     // No grant to autogroup:internet: no exit-node use.
     // No grant from tag:larpus: LARPUS cannot initiate connections to the phone.
   }
   ```

   Also: the PC node runs without `--advertise-routes` or `--advertise-exit-node`, and
   without `--ssh`. `headscale nodes list-routes` should show nothing. Policy tests
   (`"tests"` in the policy file, supported by Headscale) should assert that the Pixel can reach the gateway
   port and nothing else, and that any other node is denied. Exact syntax is confirmed against
   the pinned version (Q11).
4. **Per-request authentication at the gateway.** Every LARPUS page and API request on the
   authenticated listener checks a session cookie, plus Host/Origin, the password login and rate limits
   ([AUTH.md](AUTH.md)). **Short session lifetime:** the current fixed lifetime is 8 hours.
   For tailnet access this design proposes something shorter, for example 1 hour idle / 4 hours absolute.
   That is a **code change** for a separate PR (D4); it is not in effect today.
5. **Optional self-hosted OIDC re-authentication.** With Authelia (section 7) and a
   finite `node.expiry`, the Pixel must periodically re-authenticate to the IdP with a second
   factor before its node key is renewed. This adds to the gateway password; it does not replace it.
6. **Node approval and single-use, short-lived pre-auth keys.** No open registration:
   each node is registered by explicit owner action (`headscale nodes register`) or
   with a pre-auth key that is single-use, non-reusable, non-ephemeral, expires in 1 hour or less
   and carries the right tag. Unused keys are expired right after enrollment.
7. **Key expiry and instant revocation.** Use a finite `node.expiry` (30 days proposed).
   Lost phone: `headscale nodes expire -i <id>` cuts it off immediately, then
   `headscale nodes delete`. Then rotate the LARPUS password and restart the gateway to kill
   sessions (section 11). Revocation needs the control server to be up and reachable by
   the PC node. Peers enforce the updated netmap.
8. **Local-only access logs.** The gateway's access and auth events and Headscale's
   registration and policy logs stay on owner storage: the PC, or in R-A the off-site host, which is
   then copied home over the tailnet with no third-party log service. Client log upload
   to Tailscale Inc. is disabled (`logtail.enabled: false`, Q3).
9. **Gateway bound only to the tailnet interface.** The tailnet-facing listener binds
   only to the PC node's tailnet IP (100.64.0.0/10), never 0.0.0.0 and never a WAN address.
   The password-free loopback listener is never reachable over the tailnet. *Caveat:* the
   gateway runs on Windows, so this binding is direct only with PC option C (the Windows client). With A or B it is
   done by the tailnet container listening on its tailnet IP and forwarding to the
   authenticated listener (sections 3 and 4, Q7).

### Mapping to the SP 800-207 tenets

| # | Tenet (SP 800-207 section 2.1, paraphrased) | How this design meets it |
|---|---|---|
| 1 | All data sources and computing services are resources | The LARPUS gateway is the protected resource. Headscale and the PC node are infrastructure, not trusted zones |
| 2 | All communication is secured regardless of network location | WireGuard end to end on the tailnet, and TLS at the gateway even inside the tunnel. LAN and tailnet are treated alike |
| 3 | Access is granted per session | Gateway sessions are per login, with a short lifetime (proposed), Lock Station, invalidation on restart, and MFA step-up for sensitive actions (16.1) |
| 4 | Access is determined by dynamic policy, including client identity, application and observable state | Node key + tag (Headscale grant) and password session (gateway). Device state is limited (see gaps) |
| 5 | The integrity and security posture of all owned assets is monitored | Partial: Headscale node list/last-seen, pinned versions and local logs. No device posture (gap) |
| 6 | Authentication and authorization are dynamic and strictly enforced before access | Node approval, expiring node keys, revocation, password plus WebAuthn/TOTP MFA per session (16.1), optional OIDC with a second factor, and allowlists at three layers (16.2) |
| 7 | Collect information to improve security posture | Local-only auth audit log, ban log and PC notifications on lockout (16.4), plus periodic manual review of the node list and ACL |

### Remaining gaps (stated honestly)

- **Device posture:** stock Android with no MDM provides no attestable posture signal
  (OS patch level, root/bootloader state, screen-lock policy) to Headscale or LARPUS.
  Headscale does not support `postures`/`srcPosture`
  ([Headscale policy limitations](https://headscale.net/stable/ref/acls/#limitations)).
  Posture is therefore owner discipline: current updates, a locked bootloader and a strong screen lock.
- **No continuous evaluation / PDP:** policy is static (file reload). There is no
  risk-adaptive engine that re-scores a session mid-flight (tenet 4/5 only partly met).
- **Single administrator, single control plane:** whoever controls Headscale, the owner or, in R-A,
  the VPS host operator, can add nodes or rewrite policy. The gateway password is the backstop.
- **Session lifetime** is still 8 hours until the D4 code change lands.
- **Shared upstream IP:** with a forwarding container (PC options A/B), the gateway sees one
  source IP for all tailnet requests, so per-client rate limiting collapses to one bucket.
- **The trusted PC itself** is out of scope (same boundary as [AUTH.md](AUTH.md)).
- **Logs:** alerting is local only (16.4). There is no off-box alerting when the PC itself is down.

## 16. Hardening ("extremely secure" profile)

Design only. Every item here is a **proposal**, including every threshold. Nothing is
implemented, and each code change ships as a separate PR needing approval (section 14,
phases H1-H6). Everything is self-hosted: **no cloud MFA push services, no SMS, no email
OTP via third parties, no hosted threat or IP-reputation feeds.**

### 16.0 What the gateway does today (read from `runtime/auth.py`, `runtime/gateway.py`, AUTH.md)

| Area | Today | Gap for remote/mobile |
|---|---|---|
| Authentication | Single password, scrypt (N=16384, r=8, p=1), salt and hash in `data/password.json` | No second factor |
| Sessions | 256-bit random token, only its SHA-256 kept in memory, fixed 8 h (`Max-Age=28800`), cap of 128 sessions, Lock Station logout, all lost on restart | No idle timeout, no step-up, not bound to a device or node |
| Cookies | `HttpOnly; SameSite=Strict; Path=/`, plus `Secure` on the TLS listener | No `__Host-` prefix |
| CSRF | Exact Host check plus Origin check (when present) plus SameSite=Strict | No token; POSTs without an `Origin` header are accepted |
| Rate limits | Fixed 60 s windows: login 5/IP and 20 global; authenticated POST 30/IP; returns 429 with `Retry-After: 60`; the limiter table fails closed at 2048 keys | No escalating ban, no per-identity bucket, no separate MFA bucket |
| Inference | One global non-blocking lock (`LOCK`); a busy gateway returns 409 | Already a global cap of 1. Keep it |
| Network gate | The LAN listener rejects peers outside `LARPUS_LAN_CIDR`. **Startup refuses non-RFC1918 binds**, so the 100.64.0.0/10 tailnet range is refused today | A tailnet listener needs a code change |
| TLS | `minimum_version = TLSv1_2` | Not TLS 1.3 only; no HSTS |
| Headers | CSP `default-src 'self'` (+ `style-src 'unsafe-inline'`, `media-src blob:`), `frame-ancestors 'none'`, `base-uri 'none'`, `nosniff`, `Cache-Control: no-store` | No HSTS, Referrer-Policy, Permissions-Policy, COOP/CORP; `'unsafe-inline'` styles |
| Audit | No persistent auth audit log | Needs to be added |

### 16.1 MFA at the LARPUS gateway (layered on the existing password)

Flow: **password, then a second factor**, then a session. Neither alone grants a session.
The password check is unchanged (scrypt, constant-time compare).

- **Primary second factor: WebAuthn.** It is phishing-resistant because the credential is
  bound to the origin and RP ID ([W3C WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/#rp-id)).
  Use `userVerification: "required"`, `attestation: "none"` and ES256 (-7)
  ([spec section 5.1.3](https://www.w3.org/TR/webauthn-3/#sctn-createCredential)). Store per credential
  the credential ID, public key, `signCount`, `backupEligible` and `backupState` in a new ignored,
  owner-only `data/mfa.json`. Reject assertions whose sign count goes backwards (when it is non-zero).
  - **No-cloud caveat (important):** on a Pixel, Chrome's default passkey provider is
    Google Password Manager, which **syncs passkeys through Google's cloud**. That violates
    the no-cloud rule. Options: (a) a **hardware FIDO2 security key** over NFC/USB-C
    (device-bound, `backupEligible=false`), recommended; or (b) a device-bound
    credential, if the Pixel and Chrome version offer one without sync (Q12). The gateway should
    **reject credentials with `backupEligible=true`** so a synced passkey cannot be enrolled
    by accident. That makes it policy, not hope.
  - **Origin and TLS prerequisites:** WebAuthn only works in a secure context whose TLS was
    "established without errors", and the RP ID must be a **domain, never an IP address**
    (spec section 5.1.3 step 7). The current `https://192.168.1.2:8080` origin **cannot** use WebAuthn.
    It needs a stable hostname such as `larpus.<tailnet-base-domain>`, served to the phone
    over MagicDNS through Headscale `dns.extra_records` ([Headscale DNS docs](https://headscale.net/stable/ref/dns/)),
    so no cloud DNS is involved. It also needs a gateway certificate for that name, chained to a CA
    **the phone's Chrome trusts without warnings**. This ties to Q2 and Q6. The hostname must
    stay fixed: changing it invalidates every enrolled credential.
- **Fallback: TOTP** (RFC 6238; SHA-1, 6 digits, 30 s, ±1 step). The secret is stored encrypted
  at rest, or at minimum in the owner-only `data/` like the password file. Each time-step is
  accepted once (replay cache). Enrollment shows the secret or QR **on the PC only** (local
  listener), never over the network. Use an offline authenticator app with cloud backup off (Q13).
- **Recovery codes:** 10 single-use codes of 10 or more random characters, shown once at enrollment on the PC,
  stored only as scrypt hashes (same parameters as the password) and deleted on use.
  Using a code raises a local alert (16.4) and forces re-enrollment of a second factor.
- **Enrollment and reset are local-only:** adding or removing factors and regenerating codes is
  allowed only from the loopback listener on the PC, plus a fresh password entry.
  A remote attacker who has the password still cannot enroll their own authenticator.
- **Step-up re-authentication** (a fresh WebAuthn/TOTP check within the last 5 minutes, proposed) for
  sensitive actions: changing auth settings, exporting conversations, memory or teaching data, bulk
  delete, any future remote-admin action, and the remote kill switch (16.4). The
  implementation PR lists the exact endpoints.
- **Lockout behaviour (proposal):** 5 failed second-factor attempts per session-in-progress
  void the pending login. 10 failed MFA attempts across all sources in 15 minutes trigger an
  **MFA lockout** of the remote listener for 15 minutes, raise a local alert, and leave local
  loopback login unaffected so the owner can never be locked out of his own PC. The failure
  message stays generic ("You're Larping already"), and timing is uniform across password failure
  and MFA failure.
- **Local listener:** the password-free loopback listener stays as documented in AUTH.md. MFA
  applies to every non-loopback listener (LAN and tailnet).

**MFA on the Headscale admin and enrollment path**

- Headscale has no web admin UI here. Administration is the `headscale` CLI inside the
  pod, reachable only through `podman exec` by the owner's account. No gRPC or remote CLI API key
  is created, and the gRPC listener stays on the pod's loopback.
- Phone enrollment: with OIDC (D2), Authelia enforces `authorization_policy: two_factor` with
  WebAuthn or TOTP ([Authelia Headscale integration](https://www.authelia.com/integration/openid-connect/clients/headscale/)),
  so every node registration and expiry renewal needs a second factor. The same
  backup-eligible passkey caveat applies (Q12). Without OIDC, enrollment is a single-use
  pre-auth key created by the owner at the PC console, which is physical presence used as the factor.
- R-A off-site host: SSH key-only plus a hardware-backed key (`sk-ssh-ed25519`, FIDO2) for
  admin login (Q14).

### 16.2 Allowlisting and blocking (default deny at three layers)

Allowed principal: **the Pixel's node** (`tag:pixel`, its specific node key and its tailnet IP).
Everything else is denied at every layer independently, so one misconfiguration is not enough.

1. **Headscale policy:** the section 15 grant (`tag:pixel` to `tag:larpus` on the gateway port only).
   In addition, pin the Pixel's tailnet IP with `headscale nodes` (static assignment, Q15) so lower
   layers can match it.
2. **Host firewall:**
   - *Windows Firewall* (if the tailnet interface is on Windows, option C): an inbound allow rule for
     the gateway program on the tailnet port, **RemoteAddress = the Pixel's tailnet IP only**, scoped to the
     tailnet interface. The default inbound action stays block. Created with an elevated prompt at implementation.
   - *nftables in the tailnet-forwarder pod* (options A/B): `policy drop` on input. Accept only
     from the Pixel's tailnet IP to the forward port. Drop and log everything else to the local log.
     With userspace networking the filter is in the forwarder itself (16.3), so the
     WireGuard source is checked there (Q16).
3. **Gateway:** a tailnet listener accepts a peer only if its address equals the configured Pixel
   address, *and* (with a trusted forwarder) only if the forwarder asserts the Pixel's node identity (16.3).
   Otherwise it returns 403 before any auth processing.

**The LAN path is rejected for mobile.** The Pixel uses only the tailnet URL, even at home.
The phone is not given the LAN URL or LAN cookies, and the LAN listener keeps its subnet rule. The owner may
later decide (D5) to disable the LAN HTTPS listener entirely and use only loopback plus tailnet.

**Automatic temporary bans (local, built into the gateway; fail2ban-style):**

- Key: tailnet node identity when known, otherwise the source IP.
- Proposal: a ban after 5 failed logins **or** 5 failed MFA checks within 15 minutes. Ban durations
  double: 15 min, 30 min, 1 h, 2 h ... capped at 24 h. The strike counter decays after 24 h clean.
- A banned key gets 429 with `Retry-After` and a generic body. Every ban and unban goes into the audit log
  and triggers a local alert (16.4).
- State lives in memory plus a small owner-only file, so bans survive a gateway restart (unlike
  today's limits). The owner can clear a ban only from the local listener or CLI.
- No hosted blocklists or reputation feeds.

**R-A off-site host hardening:**

- Host firewall (nftables) `policy drop` inbound. Allow only 443/tcp (Headscale/DERP over
  HTTPS) and 3478/udp (STUN) from anywhere, plus SSH **only on the tailnet interface**.
  Outbound is limited to what Headscale needs; no update-check callbacks (Q5).
- SSH: `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PermitRootLogin no`,
  `AllowUsers <owner>`, FIDO2-backed keys, and listening only on the tailnet IP. The provider's web
  console is break-glass access (Q14).
- Auto-ban: fail2ban (or the equivalent nftables meter sets) on SSH and on Headscale's
  log for repeated failed registrations and TLS handshake floods. Local jails only.
- Full-disk encryption where the provider allows; unattended security updates; no LARPUS data.

### 16.3 Rate limiting

Separate buckets so chat traffic cannot starve login and brute force cannot hide in chat
traffic. All numbers are **proposals**:

| Bucket | Key | Proposed limit |
|---|---|---|
| Password attempts | node identity / IP, plus global | 5 / 15 min per key; 20 / 15 min global (today 5/60 s and 20/60 s) |
| MFA attempts | pending-login ID, plus node identity / IP, plus global | 5 per pending login; 10 / 15 min global (and the lockout in 16.1) |
| Authenticated API (non-chat) | session **and** node identity | 30 / min (as today) |
| Chat / inference requests | session and node identity | 6 / min, 60 / hour |
| Inference concurrency | global | **1** (keep the existing `LOCK`; a busy gateway returns 409), plus at most 1 queued request per session (Q17) |
| Request size / stream time | per request | Existing input limits; proposed 10 min max stream |

**Fixing the "one IP for everyone" gap** (section 15): with a forwarding container, every
tailnet request reaches the gateway from one upstream address. Fix, in order of preference:

1. **PC option C (Windows client):** the gateway sees the real tailnet source IP directly, and per-IP
   keys work unchanged.
2. **Trusted-proxy identity header** (options A/B): the forwarder, which terminates the
   tailnet connection and knows the WireGuard peer, adds `X-Larpus-Tailnet-Node: <node key or ID>`.
   The gateway honours it **only** when the TCP peer is the forwarder's fixed loopback/WSL address
   *and* a shared secret header matches (or a Unix socket/mTLS link is used). On every request it
   **strips and rejects** any client-supplied copy. This changes AUTH.md's "never forwarded headers"
   rule only for this authenticated, single-hop case, and needs its own review (Q18).
3. In all cases, also key limits on the **authenticated session**, which a proxy cannot collapse.

**Headscale/DERP front:**

- In R-B, Headscale is LAN-only. Pod-level nftables limits new connections to the Headscale port
  (for example 30/min per source), and its connection rate is capped.
- In R-A, the host's nftables `limit`/`meter` rules on 443/tcp (new connections per source)
  and 3478/udp (packets per source), plus fail2ban (16.2). The embedded DERP has no built-in
  throttling ([DERP docs, limitations](https://headscale.net/stable/ref/derp/#limitations)), so
  limits are set conservatively for a single phone (Q9).

### 16.4 Additional controls

- **TLS:** on every non-loopback listener and on Headscale, **TLS 1.3 only**
  (`minimum_version = TLSv1_3`). Check that the Pixel's Chrome and the Tailscale app negotiate it
  (they should). Today the gateway allows 1.2. The leaf cert is ECDSA P-256 with a one-year life, and the
  hostname SAN required by WebAuthn.
- **HSTS:** `Strict-Transport-Security: max-age=31536000` on the hostname-based tailnet
  origin, without `includeSubDomains`/`preload` (a private name; never submitted to any preload
  list). HSTS on an IP origin is ignored by browsers.
- **Cookies:** rename to `__Host-larpus_session` (forces `Secure`, `Path=/` and no `Domain`). Keep
  `HttpOnly` and `SameSite=Strict`. Proposed lifetime: 15 min idle and 4 h absolute (supersedes the
  1 h idle proposal in section 15, D4). Rotate the token on login and on step-up.
- **CSRF:** keep the Host/Origin checks, and **require** an `Origin` (or `Sec-Fetch-Site: same-origin`)
  on every state-changing request. Add a per-session synchronizer token in a custom header for
  POSTs. SameSite=Strict stays as defence in depth.
- **Security headers / CSP (no remote assets):** keep `default-src 'self'`; drop
  `'unsafe-inline'` from `style-src` (move inline styles to `style.css`, or use hashes); add
  `form-action 'self'`, `object-src 'none'`, `upgrade-insecure-requests` (TLS listeners),
  `Referrer-Policy: no-referrer`, `Permissions-Policy` that denies everything except
  `microphone=(self)` and `publickey-credentials-get=(self)`, `Cross-Origin-Opener-Policy: same-origin`,
  `Cross-Origin-Resource-Policy: same-origin` and `X-Frame-Options: DENY` (legacy). Keep `no-store`.
  All assets stay vendored, with no CDNs.
- **Auth audit log (local only):** an append-only JSON-lines file in owner-only `data/audit/`.
  It records login success/failure, MFA success/failure, factor enrollment/removal, recovery-code use,
  bans/unbans, lockouts, step-ups, session creation/expiry/logout and kill-switch use. Each entry holds
  a timestamp, event, node identity, source IP and session-hash prefix, and **never** passwords, codes,
  tokens or chat content. Rotation is size-based, with local retention of 90 days (proposal). Optionally,
  hash-chain each line to make tampering evident (Q19). Never shipped off the box, except in R-A where
  Headscale's own log is pulled home over the tailnet.
- **Local alerting:** a small local watcher (or the gateway itself) raises a **Windows toast
  notification on the PC** for: a lockout, a ban, recovery-code use, a new node registration in Headscale,
  a policy reload failure or a kill-switch use. No push service, SMS or email relay. The owner sees
  alerts the next time he is at the PC. Accepted gap: no alert reaches the phone while the
  owner is away. It may also show on the phone via the LARPUS HUD after login (Q20).
- **Remote kill switch:** an authenticated, **MFA step-up**-protected HUD action ("Close remote
  access") that immediately (1) invalidates all non-loopback sessions, (2) makes the gateway
  refuse all non-loopback requests until re-enabled **from the local listener only**, and (3)
  writes an audit entry and a local alert. It deliberately cannot be re-opened remotely.
  Network-level kill (section 13) remains: expire the node in Headscale, stop the pod, and, in
  R-A, stop the off-site host.

## 17. Open questions

- **Q1** NAT plus portproxy (no UDP/STUN) versus mirrored networking (affects all distros).
  Is mirrored mode acceptable alongside docker-desktop on this machine?
- **Q2** Does the Tailscale Android app trust a user-installed CA for the control
  server? This was not found in official docs. It must be tested on the Pixel and could block the design.
- **Q3** Remaining Tailscale client telemetry and log upload to Tailscale Inc. with a custom
  control server (Android and tailscaled). Is `logtail.enabled: false` sufficient?
  Does the client still contact `log.tailscale.com` or `controlplane.tailscale.com`?
- **Q4** For R-A: VPS versus trusted-site hardware, provider FDE support, and whether the
  provider's metadata visibility is acceptable to the owner.
- **Q5** Authelia/Authentik outbound calls (update checks, NTP, telemetry) and
  how to disable them.
- **Q6** Reuse the LARPUS CA, or create a dedicated name-constrained CA for Headscale?
- **Q7** How the Windows gateway accepts tailnet traffic (section 3/4): a code change
  for a tailnet listener versus a bridge. Its LAN-subnet check currently rejects WSL-originated traffic.
- **Q8** Rootless Podman binding to 443 needs `net.ipv4.ip_unprivileged_port_start`
  or a high-port forward. Choose one.
- **Q9** Embedded DERP limits: no `/generate_204` captive-portal support, and it is the single
  relay ([DERP docs](https://headscale.net/stable/ref/derp/)). Is that acceptable on cellular?
- **Q10** Tagged nodes and the Android app: confirm that a pre-auth key carrying `tag:pixel` works
  with the stock Android client, and that a tagged phone keeps full client function
  (the demo noted that tagged devices lack user identity for Serve; Serve is not used here).
- **Q11** Exact Headscale v0.29.x grant/`tests` syntax for the policy in section 15.
- **Q12** Can the Pixel hold a **device-bound, non-synced** WebAuthn credential in Chrome,
  or does it always go to Google Password Manager sync? If unclear, require a hardware FIDO2
  key (D6).
- **Q13** Which offline TOTP app (open source, no cloud backup) the owner will use.
- **Q14** R-A only: SSH with FIDO2 `sk-` keys, and the break-glass path when the tailnet is down
  (the provider console is third-party).
- **Q15** Static tailnet IP assignment for the Pixel in Headscale v0.29.x (rename/IP pinning
  options), so firewall rules can match it.
- **Q16** With userspace-networking tailscaled, where the source-IP allowlist is enforced
  (forwarder code versus nftables, which never sees the tailnet packets).
- **Q17** Should a second chat request wait in a short queue, or get the existing immediate 409?
- **Q18** Accept a narrowly scoped trusted-proxy header (reverses AUTH.md's "never forwarded
  headers" for one authenticated hop), or require option C?
- **Q19** Is a hash-chained audit log worth the complexity?
- **Q20** Show local alerts in the HUD after login (so the phone sees them), or keep them PC-only?

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
| 3 | Access is granted per session | Gateway sessions are per login, with a short lifetime (proposed), Lock Station, and invalidation on restart |
| 4 | Access is determined by dynamic policy, including client identity, application and observable state | Node key + tag (Headscale grant) and password session (gateway). Device state is limited (see gaps) |
| 5 | The integrity and security posture of all owned assets is monitored | Partial: Headscale node list/last-seen, pinned versions and local logs. No device posture (gap) |
| 6 | Authentication and authorization are dynamic and strictly enforced before access | Node approval, expiring node keys, revocation, the password gate per session, optional OIDC with a second factor |
| 7 | Collect information to improve security posture | Local-only Headscale and gateway logs, periodic review of the node list and ACL (manual) |

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
- **Logs** are reviewed manually; there is no alerting.

## 16. Open questions

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

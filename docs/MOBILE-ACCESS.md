# Mobile access through Tailscale with Tailnet Lock (design, not implemented)

Status: **design only. Revised 2026-10-15, 11:54 PM ET.** Nothing in this document has been executed.
Every implementation step needs explicit owner approval first. No code, script, firewall
rule, router setting or account changes with this document. See the [decision record](DECISIONS.md).

Goal: the owner reaches LARPUS from his Google Pixel while away from home.

Owner decision (2026-10-15, 11:54 PM ET): use the **Tailscale coordination service (SaaS) plus
[Tailnet Lock](https://tailscale.com/kb/1226/tailnet-lock)** instead of self-hosted Headscale.
The Headscale design is kept briefly in section 14 as the documented alternative and exit path.

## 1. Scope of the cloud exception

This is an **explicit, scoped owner exception** to the project's no-cloud principle. It covers only:

- the Tailscale **coordination plane** (node registration, key and policy distribution, and the admin console);
- Tailscale-operated **DERP relays** (which relay WireGuard ciphertext when no direct path exists);
- **Google** as the identity provider for a dedicated tailnet-only account (section 5).

It does **not** cover anything else. No inference, prompts, conversations, notes, corpus, model files,
passwords or keys go to any cloud service. Traffic between the Pixel and the PC is WireGuard end to
end. **The offline larpus pod stays network-less** (`network=none`), and nothing in
[WINDOWS-HOME-ISOLATION.md](WINDOWS-HOME-ISOLATION.md) changes. Client telemetry is turned off where
the client allows it (section 9). LARPUS's own MFA, bans, limits and audit stay self-hosted (section 11).

Rationale: home port forwarding is prohibited (below), no off-site owner hardware is available, and the
Raspberry Pi 5 at home is behind the same router, so it cannot provide inbound reachability.
A coordination service plus relays is the only way to give an outbound-only home PC remote reachability.
Tailnet Lock moves trust over *which nodes may join* back onto owner devices.

Constraints that stay:

- **No port forwarding on the home router of any kind** (no 443, no 3478, no UPnP/NAT-PMP), and no
  inbound IPv6 pinholes. The home PC makes **outbound connections only**.
- The gateway never binds to 0.0.0.0 or any WAN address. The password-free loopback listener is never
  reachable over the tailnet.
- All zero-trust (section 10) and hardening (section 11) controls stay, including the hardware FIDO2 key as the
  recommended second factor, the TOTP fallback, the three-layer Pixel-only allowlist, bans, rate limits,
  short sessions, CSP/HSTS/TLS 1.3, local audit and the kill switch.
- This supersedes [TAILSCALE_DEMO.md](TAILSCALE_DEMO.md)'s Serve-based route for ongoing access. Serve
  and Funnel are not used.

## 2. Threat model

Assets: conversations, notes, the corpus and quarantine volume, the LARPUS password and MFA secrets, the
local CA key, the Tailnet Lock keys and disablement secrets, the SSO account, and the owner's metadata.

| Adversary / failure | In scope | Mitigation |
|---|---|---|
| Internet scanners | yes | Nothing at home listens on WAN (no forwards or pinholes). The PC only dials out |
| Tailscale (malicious, compelled or breached) **injecting a node** | yes | **Tailnet Lock:** peers reject node keys not signed by a trusted lock key (section 3) |
| Tailscale **widening the ACL** or changing DNS among already-signed nodes | yes | Not covered by lock. The Windows Firewall Pixel-only rule and the gateway allowlist, password and MFA (sections 10, 11) do not depend on Tailscale |
| Tailscale **observing metadata** | accepted (exception) | Minimised: client logs off, random tailnet DNS name, non-identifying machine names (sections 7, 9). See section 6 |
| Tailscale **outage / account suspension** | accepted | LAN access is the fallback; the Headscale exit path (section 14) |
| SSO (Google) account takeover | yes | Dedicated account, two FIDO2 keys, APP, no phone recovery (section 5). Lock still blocks new unsigned nodes |
| Stolen/lost Pixel | yes | Remove the node, rotate the LARPUS password, MFA required (section 12) |
| Signing-node compromise (PC or Pi) | yes | `tailscale lock revoke-keys` co-signed by the other signer (section 3). Gateway MFA is still required |
| Password guessing / credential stuffing via the phone path | yes | MFA (11.1), per-identity and per-IP login buckets, exponential temporary bans (11.2, 11.3) |
| Stolen session cookie | yes | Secure/HttpOnly/SameSite=Strict `__Host-` cookie, short sessions, MFA step-up for sensitive actions (11.1, 11.4) |
| GPU exhaustion by a valid but abusive client | yes | Global inference concurrency of 1 and per-session chat buckets (11.3) |
| Certificate Transparency leak of hostnames | yes | Local CA by default; if `tailscale cert` is chosen, use non-identifying names (section 7) |
| Google account compromise or Google acting against the owner | yes | Dedicated account, two hardware keys, Advanced Protection; Tailnet Lock blocks node injection anyway |
| Owner's PC compromised | no | Same trusted-machine boundary as [AUTH.md](AUTH.md) |
| Nation-state / targeted Android exploit | no | Out of scope |

## 3. Tailnet Lock

How it works ([Tailnet Lock KB](https://tailscale.com/kb/1226/tailnet-lock)):

- Every node has a WireGuard **node key** and a **Tailnet Lock key (TLK)**. With lock enabled, a node key
  must be **signed by a trusted TLK**, and peers verify the signature before allowing a connection. The
  trusted TLK set lives in the **tailnet key authority** (TKA), a signed chain that the coordination
  server distributes but cannot forge.
- The model is trust on first use. After `tailscale lock init`, run `tailscale lock status` on every node and
  check that they all list the same signing keys, matching the intended signers.
- Lock and **device approval are mutually exclusive**. Here the lock signature *is* the approval step.
- Lock requires clients v1.46.1 or later. Admin-console enablement requires **at least two signing nodes**.
  A maximum of 20 signers. Rotate TLKs at most once a year.

Signing nodes:

- **The PC** (Windows client; the `tailscale lock` CLI works on Windows).
- **A second trusted signer: the Raspberry Pi 5** at home, running the Linux client (recommended, D3). It
  only dials out like the PC, so no forwarding is needed. It can co-sign key revocation and sign new nodes if
  the PC is down. Tailnet Lock keys sit on device storage ("if the device is compromised, the key can be
  obtained"), so keep the Pi minimal, updated and physically secure.
- **The Pixel cannot be a signer:** Android cannot sign, and signing-link/QR flows exist only on macOS,
  Windows and iOS. The Pixel is added with a **pre-signed, tagged, one-off auth key** produced on the PC
  (`tailscale lock sign <auth-key>`; see section 5).
- **Set a state directory on every node:** the Windows client does this automatically, and the Pi's packaged
  systemd unit sets `--state`. Without one, lock state is held in memory and re-fetched from the coordination server at startup.

**Disablement secrets:** `tailscale lock init` prints ten; any one disables lock. Store them **offline**:
printed, in two physically separate places, never in a cloud password manager. Recommendation: **do not**
send a disablement secret to Tailscale support (D8). That means if all are lost the tailnet cannot be recovered;
it would have to be recreated, which is acceptable for a two-node personal tailnet. A used secret is distributed to all nodes and must be
treated as public.

What lock **protects against**: the coordination server (malicious, compromised or compelled) **adding a node**
or **swapping a node key** so it can send or receive traffic in the tailnet. It also protects against an SSO
takeover adding devices without a signer's cooperation.

What lock **does not protect against**:

- **Metadata:** Tailscale still sees who, what, where and when (section 6).
- **Availability:** Tailscale can stop coordinating, drop relays or suspend the account.
- **Policy and configuration:** the policy file, DNS settings and the packet filters derived from them are
  delivered by the coordination server. As far as the official docs describe, lock signs node keys and the
  TLK set only, not the policy (Q2). So a hostile control plane could widen access **among already-signed nodes**
  (the Pixel, the PC and the Pi). The Windows Firewall rule and the gateway checks (section 11.2) are the
  defence that does not depend on Tailscale.
- **A compromised signer:** it can sign new nodes until revoked.
- **The endpoints themselves** (a compromised PC or phone).

## 4. Tailscale policy file (default-deny)

Tailscale access rules **deny by default**; each grant is an implicit accept
([policy syntax](https://tailscale.com/kb/1337/policy-syntax)). A tailnet that never edits its policy
gets an allow-all default plus a default SSH check rule, so the file below **replaces** the default
entirely. Proposal:

```jsonc
{
  "tagOwners": {
    "tag:pixel":  ["autogroup:admin"],
    "tag:larpus": ["autogroup:admin"],
    "tag:signer": ["autogroup:admin"]      // the Pi 5: signs only, reaches nothing
  },
  "postures": {
    // Basic posture attributes are on all plans, but they are self-reported by the client
    "posture:pixel": { "assertions": ["node:os == 'android'", "node:tsReleaseTrack == 'stable'", "node:tsVersion >= '<MIN_VERSION>'"] }
  },
  "grants": [
    { "src": ["tag:pixel"], "srcPosture": ["posture:pixel"],
      "dst": ["tag:larpus"], "ip": ["tcp:<GATEWAY_TAILNET_PORT>"] }
  ],
  // No "ssh" section, so no Tailscale SSH (this also removes the default SSH check rule).
  // No "autoApprovers"; the PC and Pi never advertise routes or exit nodes; nothing grants autogroup:internet.
  // No grant from tag:larpus or tag:signer: neither can initiate anything.
  "tests": [
    { "src": "tag:pixel",  "proto": "tcp", "accept": ["tag:larpus:<GATEWAY_TAILNET_PORT>"],
      "deny": ["tag:larpus:22", "tag:larpus:8080", "tag:larpus:3389", "tag:signer:22"] },
    { "src": "tag:signer", "proto": "tcp", "deny": ["tag:larpus:<GATEWAY_TAILNET_PORT>", "tag:pixel:443"] },
    { "src": "tag:larpus", "proto": "tcp", "deny": ["tag:pixel:443", "tag:signer:22"] }
  ]
}
```

Notes:

- `tests` run on every policy change, and a failing assertion rejects the edit. Tests take a single port
  per destination and no wildcards. Set `<GATEWAY_TAILNET_PORT>` and `<MIN_VERSION>` at implementation; also
  check whether `tests` need `srcPostureAttrs` to exercise the posture condition (Q17).
- **Is the ACL still enforced client-side under lock?** Yes. Packet filters are applied by each node's own
  client, and lock does not change that. But the filters come from the coordination server, and lock does not
  sign them (section 3). So "enforced on the device" does not mean "independent of Tailscale". Hence the
  Windows Firewall and gateway layers.
- **Tagged devices have key expiry disabled by default** ([auth keys KB](https://tailscale.com/kb/1085/auth-keys)).
  Re-enable expiry on `tag:pixel` after enrollment (section 5), and decide deliberately for `tag:larpus`/`tag:signer` (Q8).

## 5. Identity, enrollment and keys

- **Identity provider: Google** (owner decision 2026-10-15, superseding the self-hosted OIDC idea).
  Use a **dedicated Google account used only for this tailnet**, not the owner's everyday account and not used for
  Gmail, Drive or anything else. Tailscale's Google sign-in is the IdP; a tailnet must be created through an SSO
  provider, and passkey-only Tailscale users cannot create one ([passkeys KB](https://tailscale.com/kb/1269/passkeys)).
  - **Two hardware FIDO2 security keys** (primary plus backup, for example Titan or YubiKey with NFC/USB-C), both enrolled.
    The backup is stored offline with the Tailnet Lock disablement secrets. **No Android or Google Password Manager passkey**
    on this account, because GPM passkeys sync through Google's cloud and are tied to the everyday phone.
  - **Google Advanced Protection Program** (recommended, D2): free. Per Google's
    [APP FAQ](https://landing.google.com/advancedprotection/faq/) it needs at least one passkey or FIDO key and offers a
    configuration of **"2 passkeys or security keys"** as primary and secondary factors. That allows enrolling with the two hardware keys and
    **no recovery phone**. Sign-in then always needs a key, and lost-key recovery goes through Google's slow
    manual process ("may take a few days"). That trade-off is accepted, because Tailnet Lock and LAN access cover the gap.
    APP's FAQ also suggests adding recovery email and phone; **do not add a phone number** (no SMS or phone recovery).
    A recovery email only if it is itself hardware-key protected (Q16).
  - No SMS 2-step verification, no Google prompts on a phone, no backup codes stored online (if generated, print them offline).
  - **Tailnet Lock on top:** even a fully compromised Google account (or Tailscale) cannot add a node without a
    PC or Pi signature (section 3). Trust in both Google and Tailscale is limited to metadata and availability.
- **Admin console:** sessions last 30 days. Log out after each use and use a dedicated browser profile.
  No API keys, OAuth clients, webhooks or log streaming.
- **Enrollment:**
  - The PC joins first (interactive SSO login, tag `tag:larpus`), then the Pi (`tag:signer`).
  - Then `tailscale lock init` with both as signers.
  - Then the Pixel: on the admin console, generate a **one-off** (non-reusable), non-ephemeral auth key that
    expires in 1 day (the minimum) and is tagged `tag:pixel`. Sign it on the PC with
    `tailscale lock sign <auth-key>`, enter it in the Android app under **Use an auth key**, and then revoke any
    leftover keys. Tailscale revokes a one-off key automatically once used.
- **Key expiry** ([key expiry KB](https://tailscale.com/kb/1028/key-expiry)): the custom authentication period
  is 1-180 days on all plans. Proposal: **30 days** for the Pixel, with expiry explicitly re-enabled because
  it is tagged. On re-authentication, lock re-signs the new node key automatically.
- Device approval is not available alongside lock; the lock signature is the approval (section 3).

### 5.1 Alternative (not chosen): self-hosted Authelia via Tailscale custom OIDC

Kept only as a documented alternative. Tailscale's [custom OIDC KB](https://tailscale.com/kb/1240/sso-custom-oidc)
requires a **custom domain** serving `/.well-known/webfinger`, and states that *"self-hosted identity providers must be
publicly accessible on the internet."* Tailscale's servers fetch WebFinger and discovery, exchange the code at the token
endpoint and verify against JWKS, so a browser-only redirect is not enough. With no port forwarding, that would need an
outbound tunnel such as Cloudflare Tunnel, which is a second cloud dependency that terminates TLS on IdP traffic and needs
cloud DNS. Tailscale Funnel is circular for an IdP: the tailnet must exist first, the IdP host would depend on its own
login, and Funnel cannot serve the custom domain. Authelia fits without public exposure only with the Headscale exit path (section 14).

## 6. What Tailscale sees (metadata)

Even with logs off and traffic encrypted end to end, the coordination service necessarily learns:

- the SSO identity and email of the admin account, and the tailnet name;
- each device's name, OS, Tailscale version, tags, node and lock public keys, and tailnet IPs;
- each device's **public IP addresses and ports** (endpoints, reported for NAT traversal) and when it is online;
- the full **policy file** and DNS settings;
- **DERP relays** see the source and destination node, timing and volume of relayed **ciphertext** (not content);
- configuration audit logs of admin actions, retained by Tailscale for 90 days
  ([logging KB](https://tailscale.com/kb/1011/log-mesh-traffic));
- if client logging is *not* disabled, client operational logs, including connection open/close events,
  are streamed to `log.tailscale.com` (same KB).

It does **not** see traffic contents, the LARPUS password, MFA secrets, gateway cookies or anything inside
the offline pod. Network flow logs are a Premium feature and stay off.

## 7. HTTPS, MagicDNS and the WebAuthn origin

WebAuthn needs a **hostname** (not an IP) and TLS "established without errors" (section 11.1). The
stable name is the PC's MagicDNS name, `larpus.<tailnet-name>.ts.net`. Before enabling anything, switch
the tailnet to a **randomized tailnet DNS name** and give machines non-identifying names
([HTTPS KB](https://tailscale.com/kb/1153/enabling-https)). The tailnet name cannot be changed later except
between the default and random forms, and any change breaks enrolled passkeys.

| | Local CA (recommended, D7) | `tailscale cert` (Let's Encrypt) |
|---|---|---|
| Phone trust | Import the CA into Android's user store; Chrome must then treat the site as a secure context (Q5) | Publicly trusted; works with no CA install |
| Privacy | Nothing published | **Machine name and tailnet DNS name are published permanently to the Certificate Transparency public ledger** (KB: "acknowledge … will be published on a public ledger") |
| Cloud | None | Another external dependency (Let's Encrypt, plus Tailscale-hosted DNS-01 TXT records); outside the scoped exception |
| Operations | One-year leaf; reuse the [HTTPS.md](HTTPS.md) tooling | 90-day certs, **owner-run renewal** with file-based `tailscale cert`, and rate-limit lockouts |

The **Android CA question gets simpler:** the Tailscale app talks to Tailscale's control plane over public
TLS, so the earlier open question (would the app trust a self-hosted control server's CA) **no longer applies**.
Only Chrome-to-gateway trust remains (Q5). If Q5 fails, `tailscale cert` is the fallback, accepting the CT
disclosure of one non-identifying name.

## 8. PC node: the Windows client (now viable and simplest)

Recommended: the **official Tailscale Windows client** on the PC. It gives Windows a real tailnet interface
and IP, so:

- the gateway can bind **only** to that tailnet IP (a code change: today startup refuses non-RFC1918
  addresses; see 11.0 and phase H5);
- the gateway sees each peer's real tailnet IP, so per-IP limits and the Pixel-only allowlist work, and the
  forwarding-container "one IP" problem disappears;
- the Windows Firewall rule (11.2) can scope to the Tailscale interface and the Pixel's IP;
- no WSL networking change (NAT/mirrored) is needed, and the Larpus WSL distro and pods are untouched.

Settings: no `--advertise-routes`, no `--advertise-exit-node`, no `--ssh`, no Serve or Funnel. Client
logging is off (section 9). Run in unattended mode only if the owner wants remote access without being signed in to Windows (Q6).

The alternatives (tailscaled in a userspace-networking container, or in the Larpus distro) are not recommended.
They bring back the WSL interface problem and the trusted-proxy header need (Q13).

## 9. Client telemetry and logs

Each Tailscale client streams operational logs, including connection events, to `log.tailscale.com` unless
opted out ([logging KB](https://tailscale.com/kb/1011/log-mesh-traffic)). The opt-out is the
`--no-logs-no-support` flag or the `TS_NO_LOGS_NO_SUPPORT` environment variable. It "disables telemetry and
opts the device out of any support that would require that telemetry". The side effect is that **Tailscale may
be unable to provide technical support.**

- **Windows (PC):** only the environment variable works. Put `TS_NO_LOGS_NO_SUPPORT=true` in
  `%ProgramData%\Tailscale\tailscaled-env.txt` and restart the service.
- **Linux (Pi):** `TS_NO_LOGS_NO_SUPPORT=true` in `/etc/default/tailscaled`, or `--no-logs-no-support`.
- **Android (Pixel):** the KB documents **no opt-out** for the Android app. This is an accepted residual
  until resolved (Q1).
- Local logs stay local: the Windows client logs to `C:\ProgramData\Tailscale`, the Pi to journald.
  Network flow logs and log streaming are not enabled.

## 10. Zero Trust Networking (NIST SP 800-207)

This section maps the design to the seven tenets in
[NIST SP 800-207, *Zero Trust Architecture*, section 2.1](https://doi.org/10.6028/NIST.SP.800-207)
([CSRC page](https://csrc.nist.gov/pubs/sp/800/207/final)). No implicit trust is given for being on the
tailnet, on the LAN or on the owner's own phone.

Controls:

1. **Per-node key identity:** WireGuard node keys, **each signed by a Tailnet Lock key** held on owner devices.
2. **Tailnet membership grants no implicit trust:** the policy is default-deny (section 4), and the gateway still
   requires password plus MFA.
3. **Default-deny policy:** only `tag:pixel` (with Android posture) can reach `tag:larpus` on the gateway port.
   There are no routes, exit nodes or SSH, and `tests` guard it (section 4).
4. **Per-request authentication at the gateway** with short sessions: 15 min idle / 4 h absolute, proposed (D4, 11.4).
5. **Re-authentication:** node key expiry every 30 days through the dedicated Google account (two FIDO2 keys, APP), plus
   gateway MFA step-up for sensitive actions (11.1).
6. **Enrollment control:** one-off, short-lived, tagged auth keys that must be **pre-signed by a lock signer**.
7. **Expiry and revocation:** see section 12.
8. **Local-only access logs:** the gateway audit (11.4). Client logs are opted out (section 9).
9. **Gateway bound only to the tailnet interface**, never 0.0.0.0 or WAN (section 8, phase H5).

| # | Tenet (SP 800-207 section 2.1, paraphrased) | How this design meets it |
|---|---|---|
| 1 | All data sources and computing services are resources | The gateway is the protected resource. Tailscale, the PC node and the Pi are infrastructure, not trusted zones |
| 2 | All communication is secured regardless of network location | WireGuard end to end (DERP relays ciphertext only) plus TLS 1.3 at the gateway inside the tunnel |
| 3 | Access is granted per session | Gateway sessions per login, short lifetime, MFA step-up, invalidated on restart |
| 4 | Access is determined by dynamic policy | Signed node key, tag and basic posture (Tailscale grant), then the Pixel-IP firewall rule, then password plus MFA session |
| 5 | Integrity and security posture of assets is monitored | Partial: basic self-reported posture, `tailscale lock status`, local audit. No MDM-grade posture (gap) |
| 6 | Authentication and authorization are dynamic and strictly enforced before access | Lock signatures, expiring node keys, password plus WebAuthn/TOTP, allowlists at three layers (11.2) |
| 7 | Collect information to improve security posture | Local auth audit, ban log and PC notifications (11.4). Periodic manual review of devices, lock status and the policy |

Remaining gaps (stated honestly):

- **Device posture:** stock Android with no MDM gives no attested posture. Tailscale's basic attributes (OS,
  client version) are **self-reported**; MDM and EDR integrations need a paid plan and an MDM
  ([device posture KB](https://tailscale.com/kb/1288/device-posture)). Root, bootloader and screen-lock state
  are owner discipline.
- **The policy is not lock-protected:** the coordination server delivers filters and DNS (section 3). Layers 2
  and 3 of 11.2 compensate.
- **The metadata exception** (section 6) and **availability** depend on Tailscale.
- **The identity provider is Google** (cloud). Tailnet Lock limits what an IdP compromise can do.
- **No continuous evaluation engine:** static policy, manual review.
- **Signer keys** are stored in software on the PC and Pi.
- **Session lifetime** stays 8 hours until H1/D4 land. **Alerts** are PC-local only.
- **No per-node signature revocation** is documented short of deleting the node. Revoking a TLK invalidates every
  node it signed (Q7).

## 11. Hardening ("extremely secure" profile)

Design only. Every item here is a **proposal**, including every threshold. Nothing is
implemented, and each code change ships as a separate PR needing approval (section 15,
phases H1-H6). Everything is self-hosted: **no cloud MFA push services, no SMS, no email
OTP via third parties, no hosted threat or IP-reputation feeds.** (The Tailscale exception in section 1
covers the coordination plane and DERP only, not any of these controls.)

### 11.0 What the gateway does today (read from `runtime/auth.py`, `runtime/gateway.py`, AUTH.md)

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

### 11.1 MFA at the LARPUS gateway (layered on the existing password)

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
    credential, if the Pixel and Chrome version offer one without sync (Q9). The gateway should
    **reject credentials with `backupEligible=true`** so a synced passkey cannot be enrolled
    by accident. That makes it policy, not hope.
  - **Origin and TLS prerequisites:** WebAuthn only works in a secure context whose TLS was
    "established without errors", and the RP ID must be a **domain, never an IP address**
    (spec section 5.1.3 step 7). The current `https://192.168.1.2:8080` origin **cannot** use WebAuthn.
    It needs a stable hostname: the PC's MagicDNS name `larpus.<tailnet-name>.ts.net`
    (section 7). It also needs a gateway certificate for that name that **the phone's Chrome trusts without
    warnings**, from either the local CA or `tailscale cert` (D7, Q5). The hostname and the tailnet
    DNS name must stay fixed: changing either invalidates every enrolled credential.
- **Fallback: TOTP** (RFC 6238; SHA-1, 6 digits, 30 s, ±1 step). The secret is stored encrypted
  at rest, or at minimum in the owner-only `data/` like the password file. Each time-step is
  accepted once (replay cache). Enrollment shows the secret or QR **on the PC only** (local
  listener), never over the network. Use an offline authenticator app with cloud backup off (Q10).
- **Recovery codes:** 10 single-use codes of 10 or more random characters, shown once at enrollment on the PC,
  stored only as scrypt hashes (same parameters as the password) and deleted on use.
  Using a code raises a local alert (11.4) and forces re-enrollment of a second factor.
- **Enrollment and reset are local-only:** adding or removing factors and regenerating codes is
  allowed only from the loopback listener on the PC, plus a fresh password entry.
  A remote attacker who has the password still cannot enroll their own authenticator.
- **Step-up re-authentication** (a fresh WebAuthn/TOTP check within the last 5 minutes, proposed) for
  sensitive actions: changing auth settings, exporting conversations, memory or teaching data, bulk
  delete, any future remote-admin action, and the remote kill switch (11.4). The
  implementation PR lists the exact endpoints.
- **Lockout behaviour (proposal):** 5 failed second-factor attempts per session-in-progress
  void the pending login. 10 failed MFA attempts across all sources in 15 minutes trigger an
  **MFA lockout** of the remote listener for 15 minutes, raise a local alert, and leave local
  loopback login unaffected so the owner can never be locked out of his own PC. The failure
  message stays generic ("You're Larping already"), and timing is uniform across password failure
  and MFA failure.
- **Local listener:** the password-free loopback listener stays as documented in AUTH.md. MFA
  applies to every non-loopback listener (LAN and tailnet).

**MFA on the Tailscale admin and enrollment path:** see section 5 (a dedicated SSO account with
two FIDO2 keys and Advanced Protection). Enrolling the Pixel also needs a
**Tailnet Lock signature from the PC**, which acts as physical presence (section 3). No Tailscale API keys or OAuth
clients are created.

### 11.2 Allowlisting and blocking (default deny at three layers)

Allowed principal: **the Pixel's node** (`tag:pixel`, its specific node key and its tailnet IP).
Everything else is denied at every layer independently, so one misconfiguration is not enough.

1. **Tailscale policy:** the section 4 grant (`tag:pixel` to `tag:larpus` on the gateway port only).
   This layer is delivered by the coordination server, so it is **not** protected by Tailnet Lock
   (section 3). That is why layers 2 and 3 exist and do not depend on Tailscale. The Pixel's tailnet IP
   is stable for the life of the node (Q11), so lower layers can match it.
2. **Host firewall:**
   - *Windows Firewall* (the chosen PC option, section 8): an inbound allow rule for the gateway
     program on the tailnet port, **RemoteAddress = the Pixel's tailnet IP only**, scoped to the
     Tailscale interface. The default inbound action stays block. Created with an elevated prompt at implementation.
3. **Gateway:** a tailnet listener accepts a peer only if its address equals the configured Pixel
   address (the Windows client gives the gateway the real tailnet source IP).
   Otherwise it returns 403 before any auth processing.

**The LAN path is rejected for mobile.** The Pixel uses only the tailnet URL, even at home.
The phone is not given the LAN URL or LAN cookies, and the LAN listener keeps its subnet rule. The owner may
later decide (D5) to disable the LAN HTTPS listener entirely and use only loopback plus tailnet.

**Automatic temporary bans (local, built into the gateway; fail2ban-style):**

- Key: tailnet node identity when known, otherwise the source IP.
- Proposal: a ban after 5 failed logins **or** 5 failed MFA checks within 15 minutes. Ban durations
  double: 15 min, 30 min, 1 h, 2 h ... capped at 24 h. The strike counter decays after 24 h clean.
- A banned key gets 429 with `Retry-After` and a generic body. Every ban and unban goes into the audit log
  and triggers a local alert (11.4).
- State lives in memory plus a small owner-only file, so bans survive a gateway restart (unlike
  today's limits). The owner can clear a ban only from the local listener or CLI.
- No hosted blocklists or reputation feeds.

There is no off-site host in this design, so the earlier off-site hardening is dropped.

### 11.3 Rate limiting

Separate buckets so chat traffic cannot starve login and brute force cannot hide in chat
traffic. All numbers are **proposals**:

| Bucket | Key | Proposed limit |
|---|---|---|
| Password attempts | node identity / IP, plus global | 5 / 15 min per key; 20 / 15 min global (today 5/60 s and 20/60 s) |
| MFA attempts | pending-login ID, plus node identity / IP, plus global | 5 per pending login; 10 / 15 min global (and the lockout in 11.1) |
| Authenticated API (non-chat) | session **and** node identity | 30 / min (as today) |
| Chat / inference requests | session and node identity | 6 / min, 60 / hour |
| Inference concurrency | global | **1** (keep the existing `LOCK`; a busy gateway returns 409), plus at most 1 queued request per session (Q12) |
| Request size / stream time | per request | Existing input limits; proposed 10 min max stream |

**The "one IP for everyone" gap is resolved** by the Windows client (section 8): the gateway sees
the real tailnet source IP, so per-IP keys work unchanged, and limits are also keyed by the authenticated
session. The trusted-proxy header idea is needed only if the container option is ever chosen (Q10).

**Coordination/DERP front:** operated by Tailscale; nothing at home listens on WAN, so there is no
front for us to rate-limit. Availability is accepted as Tailscale's (section 2).

### 11.4 Additional controls

- **TLS:** on every non-loopback gateway listener, **TLS 1.3 only**
  (`minimum_version = TLSv1_3`). Check that the Pixel's Chrome and the Tailscale app negotiate it
  (they should). Today the gateway allows 1.2. The leaf cert is ECDSA P-256 with a one-year life, and the
  hostname SAN required by WebAuthn.
- **HSTS:** `Strict-Transport-Security: max-age=31536000` on the hostname-based tailnet
  origin, without `includeSubDomains`/`preload` (a private name; never submitted to any preload
  list). HSTS on an IP origin is ignored by browsers.
- **Cookies:** rename to `__Host-larpus_session` (forces `Secure`, `Path=/` and no `Domain`). Keep
  `HttpOnly` and `SameSite=Strict`. Proposed lifetime: 15 min idle and 4 h absolute (supersedes the
  earlier 1 h idle proposal, D4). Rotate the token on login and on step-up.
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
  hash-chain each line to make tampering evident (Q14). Never shipped off the box.
- **Local alerting:** a small local watcher (or the gateway itself) raises a **Windows toast
  notification on the PC** for: a lockout, a ban, recovery-code use, a new or locked-out node (seen with `tailscale lock status`/`tailscale status`),
  or a kill-switch use. No push service, SMS or email relay. The owner sees
  alerts the next time he is at the PC. Accepted gap: no alert reaches the phone while the
  owner is away. It may also show on the phone via the LARPUS HUD after login (Q15).
- **Remote kill switch:** an authenticated, **MFA step-up**-protected HUD action ("Close remote
  access") that immediately (1) invalidates all non-loopback sessions, (2) makes the gateway
  refuse all non-loopback requests until re-enabled **from the local listener only**, and (3)
  writes an audit entry and a local alert. It deliberately cannot be re-opened remotely.
  Network-level kill (section 12) remains: remove the Pixel in the admin console and run `tailscale down` on the PC.

## 12. Revocation, lost phone and kill switch

Lost or stolen Pixel, in order:

1. In the admin console, **remove the Pixel** (Machines, then Remove). This deauthorizes it; revoking an auth key
   alone does not ([auth keys KB](https://tailscale.com/kb/1085/auth-keys)).
2. Rotate the LARPUS password (`python -m runtime.auth`) and restart the gateway, which kills all sessions.
3. Remove the lost phone's WebAuthn/TOTP enrollment locally (11.1).
4. Check `tailscale lock status` and `tailscale status` on the PC for unexpected nodes.

Signer compromise: run `tailscale lock revoke-keys` on the healthy signer, then co-sign as the KB describes.
Nodes signed only by the revoked key need re-signing.

Kill switch, in increasing severity:

1. The HUD remote kill switch (11.4): non-loopback access closes and can only be re-opened locally.
2. `tailscale down` on the PC (outbound-only, so remote reachability ends at once).
3. Disable or uninstall the Windows Tailscale client. Remove the firewall rule and the tailnet gateway listener.
4. Delete the tailnet. Keep the disablement secrets until this is done.

LAN and local LARPUS keep working at every step. Nothing touches the frozen release or the offline pod.

## 13. Plans and paid tiers

Everything this design needs is on the free **Personal** plan, which is for **non-commercial** use
([pricing](https://tailscale.com/pricing)). That covers grants/ACLs, tests, tags, auth keys, custom key
expiry, MagicDNS/HTTPS, basic posture attributes and passkeys. **Tailnet Lock** is listed for "Personal and
Enterprise" plans ([Tailnet Lock KB](https://tailscale.com/kb/1226/tailnet-lock)). Paid-only and **not used**:
MDM/EDR posture integrations, network flow logs, log streaming, custom SSH check periods, advanced roles.
Device approval exists but conflicts with lock. Google sign-in keeps the tailnet on the Personal plan. If LARPUS use ever became
commercial, the plan would need review (Q18).

## 14. Alternative and exit path: self-hosted Headscale (brief)

The earlier design (in git history on this branch, commits 596001f to c0fc4b5) used
[Headscale](https://github.com/juanfont/headscale) with an embedded DERP in an isolated rootless pod, with the
stock Android app pointed at a custom control URL. It removes the coordination-plane exception, but it **needs
inbound reachability**: an off-site owner host, or home forwarding, which is prohibited. Without that it is
LAN-only. It is the exit path if Tailscale becomes unacceptable or unavailable, or if owner-controlled off-site
hardware appears. The policy file, the hardening (section 11) and the gateway changes carry over unchanged;
only the control plane and DERP move. Tailscale's own KB notes Headscale as the way to keep the control plane
on your own infrastructure.

## 15. Implementation plan (NOT executed, requires owner approval per step)

0. The owner decides D2 (Advanced Protection), D3 (Pi as second signer), D4, D5, D6, D7, D8 and the thresholds.
1. Create the dedicated Google account. Enroll two FIDO2 keys, enroll in Advanced Protection, add no phone. Create the tailnet. Choose the random tailnet DNS
   name. Paste the section 4 policy **before** adding devices.
2. PC: install the Windows client, set `TS_NO_LOGS_NO_SUPPORT=true`, log in, and tag `tag:larpus`.
3. Pi 5: install the Linux client, set `TS_NO_LOGS_NO_SUPPORT=true`, and tag `tag:signer`.
4. `tailscale lock init` with the PC and Pi as signers. Store the disablement secrets offline. Verify
   `tailscale lock status` on both.
5. Pixel: create a pre-signed one-off tagged auth key, enroll it, re-enable key expiry (30 d), and verify `tailscale lock status`.
6. Acceptance on cellular: the Pixel reaches only the gateway port; the policy `tests` pass; the PC and Pi cannot reach
   the Pixel; a direct versus DERP path is observed; nothing at home is reachable from WAN.
7. Then the gateway code PRs below. Update STATUS.md, LAN.md and DECISIONS.md with the actual results.

**Hardening code PRs (section 11), each a separate PR with tests, each needing owner approval
before merge and before activation as a release:**

- **H1 Transport and headers:** TLS 1.3 only, HSTS on the hostname origin, CSP tightening,
  extra security headers and the `__Host-` cookie. Short idle/absolute sessions (D4).
- **H2 Audit log and local alerts:** append-only auth audit log, Windows toast watcher.
- **H3 Rate limits and bans:** separate login/MFA/chat buckets, per-session keys,
  persistent exponential bans, and the CSRF token plus mandatory Origin.
- **H4 MFA:** TOTP, hashed recovery codes and lockout first, then WebAuthn once the MagicDNS hostname and
  trusted TLS exist (Q5, D6, D7). Step-up for sensitive actions. Local-only enrollment.
- **H5 Tailnet listener:** bind only to the PC's Tailscale IP (lifting the RFC1918-only startup check for
  that one 100.64.0.0/10 address), the Pixel-IP allowlist, and the remote kill switch.
- **H6 Infrastructure (no repo code):** the Windows Firewall Pixel-only rule (elevated). It runs only after explicit approval.

## 16. Open questions

Resolved by this revision: the self-hosted control-server CA question (the Tailscale app uses public TLS), WSL
networking mode (the Windows client needs none), rootless port 443, embedded DERP limits, off-site host choices,
Authelia/Authentik outbound calls for Headscale, and Headscale policy syntax and IP pinning.

- **Q1** The Android Tailscale app has no documented telemetry or log opt-out. Is there one (for example a
  hidden setting or managed config), or is this an accepted residual?
- **Q2** Confirm from the [Tailnet Lock white paper](https://tailscale.com/kb/1230/tailnet-lock-whitepaper)
  that lock signs node keys and the TLK set only, not policy, DNS or filters.
- **Q3** Pi 5 as a signer: OS hardening level, and what else runs on it (proposal: nothing).
- **Q4** Where exactly the offline disablement secrets and SSO recovery codes are kept (two physical locations).
- **Q5** Does Chrome on the Pixel treat a site whose certificate chains to a **user-installed** CA as a secure
  context for WebAuthn without warnings? If not, use `tailscale cert` (D7).
- **Q6** Windows client: should it run unattended (before Windows sign-in), and does that change who can
  control it locally?
- **Q7** Under lock, is there a way to revoke one non-signer node's signature other than deleting it in the
  admin console?
- **Q8** Key expiry for `tag:larpus` and `tag:signer` (tagged default: off). Proposal: enabled, with a calendar reminder.
- **Q9** Can the Pixel hold a **device-bound, non-synced** WebAuthn credential in Chrome, or does it always go
  to Google Password Manager sync? If unclear, require a hardware FIDO2 key (D6).
- **Q10** Which offline, open-source TOTP app with cloud backup off the owner will use.
- **Q11** Confirm the Pixel's tailnet IP stays stable across re-authentication and key expiry, so the
  firewall rule can match it.
- **Q12** Should a second chat request wait in a short queue, or get the existing immediate 409?
- **Q13** Only if the container PC option is ever chosen: accept a narrowly scoped trusted-proxy header?
- **Q14** Is a hash-chained audit log worth the complexity?
- **Q15** Show local alerts in the HUD after login, or keep them PC-only?
- **Q16** Google account recovery: whether to add a recovery email (which must itself be hardware-key protected) or none, and how APP lost-key recovery behaves with no phone on file.
- **Q17** Exact `tests` syntax for the posture-gated grant (`srcPostureAttrs`), and the minimum Android client version.
- **Q18** Confirm that LARPUS use is non-commercial (Personal plan terms) and that Tailnet Lock remains on the
  Personal plan.
- **Q19** Tailscale re-authentication with an APP Google account on the Pixel: confirm the FIDO2 key works over NFC in the Tailscale app's login browser flow.

Decisions needed from the owner: **D2** enroll the dedicated Google account in Advanced Protection (recommended) and buy two FIDO2 keys; **D3** Pi 5 as second signer;
**D4** session lifetime (15 min idle / 4 h, proposed); **D5** disable the LAN HTTPS listener and use only loopback
plus tailnet; **D6** hardware FIDO2 key (recommended) versus a device-bound passkey, with TOTP as fallback;
**D7** local CA (recommended) versus `tailscale cert` with CT disclosure; **D8** do not escrow a disablement
secret with Tailscale support (recommended); plus all thresholds and approval of H1-H6.

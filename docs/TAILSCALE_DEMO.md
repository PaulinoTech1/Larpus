# Private Pixel demo on October 17

Prepared for the owner's Pixel 10 Pro XL over cellular. Friends watch or ask
questions through that phone; they do not receive accounts, client access, models
or source archives. This explicitly extends the earlier home-LAN-only policy to
an owner-controlled private VPN. It does not authorize public hosting.

## Connection and maintenance scope

Pixel Chrome -> Tailscale private HTTPS Serve on PC:443 -> loopback bridge:8088
-> existing authenticated LAN HTTPS gateway:8080 -> sealed model and CPU voice.

`scripts/tailscale_bridge.py` is standalone owner tooling. It neither imports nor
starts inference, changes gateway authentication, nor changes frozen release files.
It pins its upstream at startup to the active pointer's RFC1918 LAN HTTPS listener
and verifies the existing local CA and IP certificate. A preflight requires HTTP
401 from `/api/personas` without a session. It never targets the password-free
127.0.0.1:8080 listener. If the active address/port changes, stop and recheck bridge.

The bridge listens only on 127.0.0.1 and requires the exact PC tailnet Host, HTTPS
Origin on POST, and Serve's exact `Tailscale-User-Login` owner identity. Tagged
devices lack that user identity and are intentionally unsupported. Local owner
processes can spoof headers; this is the same trusted-machine boundary as the
existing localhost service. No identity/forwarding headers are sent to the gateway.
The existing password, Secure/HttpOnly/SameSite cookies, output controls, input
limits and voice service remain in use. Remote requests share a PC upstream IP
for application rate limiting. Streaming is forwarded incrementally, including
voice API responses; no whole-answer buffering is added.

Tailscale installation adds an OS networking service and external coordination
dependency, outside the sealed model. Model tools do not receive network access.
Tailscale handles transport, not model inference. Serve HTTPS certificates involve
public certificate transparency records of the machine DNS name; use a neutral
machine name before enabling HTTPS if that matters. No prompt logging is added.

## Owner setup

1. Install the official Windows Tailscale client on the PC and Android client on
   the Pixel. Sign into the same owner account; enable account MFA. Keep both
   devices untagged and do not share the PC or invite demo participants.
   Windows installation can require Administrator/UAC approval. Official guides:
   [Windows](https://tailscale.com/docs/install/windows) and
   [Android](https://tailscale.com/docs/install/android).
2. Run `powershell -NoProfile -File scripts/prepare-tailscale-demo.ps1`.
   This reads status and reports the PC DNS name/IP; it exposes nothing.
3. Review the tailnet policy in the Tailscale admin console. Substitute the actual
   Pixel and PC Tailscale IPv4 addresses in `deploy/tailscale/policy.example.json`.
   Its grant permits only the Pixel /32 to the PC /32 on TCP 443. Existing broad
   `acls` or `grants` remain additive: merely appending this grant DOES NOT restrict
   them. Remove overlapping broad access in a fresh dedicated tailnet, or carefully
   revise existing policy without disturbing unrelated services. Use policy tests
   to verify Pixel access to PC:443, denial from other devices, and denial to model,
   bridge, RDP and other PC ports. Do not paste placeholder addresses as real policy.
4. Run `powershell -NoProfile -File scripts/prepare-tailscale-demo.ps1 -WriteConfig`.
   It creates ignored `data/tailscale/bridge.json` from the signed-in PC's DNS name
   and owner login, retains any existing config, then checks the upstream. It does
   not enable Serve or change policy. Login identity is not a reusable auth token.
5. Start the bridge in a dedicated owner terminal:

   ```powershell
   python scripts/tailscale_bridge.py --check
   python scripts/tailscale_bridge.py
   ```

6. In another terminal inspect `tailscale serve status --json` and
   `tailscale funnel status`. If other routes exist, preserve and review them before
   changing anything. Once Pixel-only policy is verified, enable the private route:

   ```powershell
   tailscale serve --https=443 http://127.0.0.1:8088
   ```

   Use Serve, never Funnel. This foreground command is intentional: Ctrl+C ends
   the demo route; no persistent background publication or startup task is added.
   Serve may prompt you to enable tailnet HTTPS; follow its official setup link.
   Do not add a Windows inbound rule for port 8088, router forwarding, subnet routes,
   exit-node advertising or Ollama exposure. Confirm Serve status points at 8088.
7. On Pixel, connect Tailscale, disable Wi-Fi, and open the printed HTTPS URL in
   Chrome. Log in with the existing LARPUS password. A new browser origin has its
   own local conversation/profile storage; existing home-LAN history is not moved.
   No local CA installation on Pixel is needed for the Serve HTTPS address.

See [Serve](https://tailscale.com/docs/features/tailscale-serve),
[Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve), and
[grants](https://tailscale.com/docs/reference/syntax/grants). Serve supplies and
sanitizes owner identity headers; Funnel does not and is public. No remote claim
is established by the local bridge tests: actual Serve headers and DNS behavior
still require an end-to-end rehearsal.

## Pixel rehearsal and demonstration

- Confirm the login page and full HUD fit the portrait display, then try landscape.
- Enable voice with a tap. Start with typed input plus spoken replies, then grant
  Chrome microphone permission and test push-to-talk. Use headphones if echo occurs.
- Check spoken output, pause/resume/repeat and a complete streamed tutor answer.
- Lock/unlock the phone; reconnect Tailscale and reload if needed. Confirm the
  conversation persists on the same origin. Test a brief cellular disconnect.
- With Tailscale disconnected, the service must be inaccessible. A different
  device must be denied by tailnet policy; an incorrect application password must
  fail. Do not verify authorization by handing friends owner credentials.
- Pick a familiar supported topic and a fresh demo conversation. Ask for one
  diagnostic question, an explanation, a hint after an incomplete answer, a change
  in teaching style and an author/source citation. Only demo activated features.
- Reserve a period when GPU notes are not running. This setup does not pause or
  modify the nightly task. Keep the PC awake, plugged in and connected. Rehearse
  before October 17; keep a short recording for connectivity failure.

## Stop and recover

Stop foreground Serve with Ctrl+C. Inspect its status; if the route remains, use
`tailscale serve --https=443 off` for this dedicated route only. Do not use a global
reset when unrelated Serve routes exist. Stop the bridge with Ctrl+C. The home-LAN
gateway, model, CPU voice and note schedule continue unchanged. Keep the existing
LAN URL available as the at-home fallback. After a gateway process update a new
application login can be required, as with ordinary LAN access.

## Preparation evidence

Source/unit tests cover retained password auth, Secure cookies, HUD headers,
voice roundtrip and NDJSON streaming with mocked model/voice calls, rejection of
wrong identity/Host/Origin/framing, unsafe upstream configuration and unavailable
upstream. A private local preparation receipt can be retained under
`data/tailscale/preparation-check.json`. These checks do not prove actual tailnet
policy, cellular latency, microphone capture, physical playback or Android usability.

Goal: owner-only Pixel cellular access to the existing HUD and CPU voice.
Authority: owner requested Tailscale preparation for an October 17 personal demo;
this is an explicit exception to earlier home-LAN-only access, not public hosting.
Constraints: keep gateway/model/voice running; no frozen payload edits, public
Funnel, router forwarding, model LAN exposure, friend accounts or commit/push.
Inputs: active LAN HTTPS address, existing CA, owner's Tailscale login and DNS name.
Outputs: loopback-only authenticated HTTPS-upstream bridge, configuration template,
Pixel-only grants template, setup/reversal and cellular acceptance instructions.
Done when: source checks, mocked HTTP/auth/streaming/voice tests, real upstream
unauthenticated checks and isolated suite pass; report remote/device tests pending.
Choice: standalone owner bridge outside the model; pin upstream to active RFC1918
HTTPS listener, verify existing CA, retain existing application password and cookie.
Validate external Host/Origin and Serve owner identity; translate only those headers
required for the LAN gateway. Stream responses without buffering the whole answer.
Alternative: proxy localhost directly would bypass the application password.
Alternative: change gateway origins/listeners would require production activation.
Alternative: subnet routing grants unnecessary LAN reach and complicates Windows.
Maintenance scope: install/login Tailscale separately, inspect current tailnet policy,
restrict to Pixel /32 and PC:443, enable Serve only after local preflight. No new
Windows inbound bridge firewall rule; bridge stays 127.0.0.1. Existing LAN unchanged.
Rollback: disable this Serve route and stop bridge; leave gateway and LAN running.
Tailscale installation/account login and Pixel browser checks remain owner steps
until available. AgentDB unavailable; build contract is recorded here.

Validation: isolated suite ran 167 tests, OK with one skip; five bridge integration
tests passed. PowerShell parser and new-file whitespace checks passed. Live local
bridge smoke check verified the active upstream certificate, login page HTTP 200
and protected personas HTTP 401, without inference. Receipt ignored under data.
Tailscale absent; prerequisite checker reports this without installing/exposing.
No gateway restart, activation, policy change, Serve/Funnel route or GPU work.
Actual Tailscale/Pixel cellular, microphone, speaker and unauthorized-device tests
remain pending installation, owner sign-in and tailnet policy configuration.

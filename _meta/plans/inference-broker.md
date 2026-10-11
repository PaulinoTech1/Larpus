# Inference broker and namespace separation
Goal: restrict agent access to chat/status; raw Ollama is unreachable from agent.
Constraints: one existing loaded GPU model, offline cached images, no host ports,
no cloud/credentials or model/quarantine mounts in broker. Preserve voice/deadline.
Inputs: approved model/config, bounded messages/options; fixed model-pod loopback.
Outputs: stdlib Unix HTTP broker, Unix client, independent network-none agent,
pinned broker/image/socket-volume profile, release checks and rollback evidence.
Done when: allowlist/size/stream/failure tests, real raw-TCP denial and Unix chat,
nightly generation, complete release gates, activation/previous rollback retained.
Alternatives: loopback proxy without namespace split is bypassable; published TCP
adds exposure; choose a private Unix socket volume and separate agent namespace.
Maintenance scope: create candidate broker beside current runtime, same model pod;
new agent network=none, socket mount read-only, quarantine unchanged. No model or
voice replacement, no existing frozen files modified. Switch gateway only after
preparation. Stop prior raw-access agent after cutover and restart it for rollback.
Private broker volume survives stop for restart; socket recreated only by broker.
Context fixed at configured131072, GPU99, output<=6000 for notes, no tools/images,
no model administration, redirects, arbitrary hosts or unexpected fields.
Broker bounds API reachability/resources, not prompt semantics or DLP correctness.

Outcome 2026-10-11: activated fc4f6e6f7b33447c915afb2e9e0b9c92 after full gates.
Real Unix chat/stream/JSON, raw/external/LAN/DNS denial, admin/context rejection,
broker-loss fail closed and pinned broker restart verified. Actual HUD chat and
stream now pass with derived-note previews; fixed an existing missing text/date
schema assumption and added a normal/stream regression. LAN remains401 unauth.
69 skills clean, same8 MCP warnings retained. Model/voice unchanged; nightly
writer restarted on new agent with existing deadline. No commit/push, host reboot,
real rollback or physical browser acceptance. Evidence: docs/INFERENCE_BROKER.md.

# Kickoff choices

Goal: local home/LARP station with torus HUD and config-driven Ollama chat.
Constraints: no runtime external network, no accounts, single owner, 24 GB VRAM.
Inputs: user brief, existing MIT license, verified upstream docs.
Outputs: static HUD, Python gateway, personas/schema, architecture/voice plan.
Done when: gateway contract and failure tests pass; UI renders locally; live
Ollama/sandbox/voice limitations are explicitly recorded.

Options: React + API (extra build/dependencies); Python + static UI (chosen,
stdlib runtime and offline assets); Tauri app (defer until voice integration).
Art direction: calm technical readiness, cyan wireframe torus, monospace readouts,
asymmetric three-column station. Avoid fake telemetry and remote decorative assets.
AgentDB unavailable in this environment; no repository-specific guidance found.

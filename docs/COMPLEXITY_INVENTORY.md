# Complexity inventory

AST decision count:1 + branches/loops/handlers/boolean alternatives/comprehensions/non-default match cases. Nested functions measured separately; not a formal whole-program complexity proof.

## Largest decision counts

| Function | Decisions | Lines |
| --- | ---: | ---: |
| runtime/knowledge.py:_retrieve | 103 | 113 |
| runtime/gateway.py:Handler.do_POST | 74 | 156 |
| runtime/isolation.py:validate_container | 59 | 60 |
| scripts/prepare-knowledge.py:build | 51 | 94 |
| runtime/isolation.py:preflight | 47 | 52 |
| runtime/health.py:check | 45 | 107 |
| runtime/inference_broker.py:Handler.route | 45 | 60 |
| runtime/inference.py:chat | 35 | 96 |
| runtime/knowledge.py:_hybrid | 35 | 35 |
| scripts/research-archive.py:main | 34 | 67 |
| scripts/github_archive.py:indexed_records | 34 | 64 |
| runtime/inference_broker.py:validate_chat | 34 | 28 |
| scripts/tailscale_bridge.py:Bridge.relay | 33 | 47 |
| scripts/github_archive.py:snapshot | 32 | 61 |
| runtime/capability_trials.py:validate | 29 | 32 |
| scripts/study-notes.py:answers | 28 | 37 |
| runtime/voice.py:preflight | 28 | 22 |
| runtime/skills.py:load_skills | 26 | 34 |
| runtime/knowledge.py:study_notes | 26 | 29 |
| runtime/capability_trials.py:bank | 26 | 20 |
| runtime/inference_broker.py:Handler.managed_chat | 24 | 41 |
| runtime/agents.py:load_personas | 23 | 27 |
| runtime/capability_trials.py:profile | 23 | 24 |
| scripts/research-archive.py:fetch_one | 22 | 50 |
| runtime/namespace_probe.py:check | 22 | 41 |

## Highest import fan-in

| Module | Importers | Imports |
| --- | ---: | ---: |
| runtime.skills | 13 | 1 |
| runtime.agents | 12 | 2 |
| runtime.text_filter | 11 | 0 |
| runtime.isolation | 7 | 2 |
| runtime.knowledge | 7 | 7 |
| runtime.diagnostics | 6 | 0 |
| runtime.dlp | 5 | 1 |
| runtime.mcp_client | 5 | 3 |
| runtime.context | 4 | 1 |
| runtime.local_ollama | 4 | 0 |
| runtime.security_scan | 4 | 2 |
| runtime.provenance | 3 | 0 |

Not checked: JavaScript/PowerShell function complexity, dynamic imports/exec, runtime call frequencies, cross-process wait graphs.

This is an inventory, not a quality score. High counts are review targets. Baseline allowances retain visible existing debt; new functions default to 12 decisions/80 lines. Do not reset the baseline to bypass a failure.

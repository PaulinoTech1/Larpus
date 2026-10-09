# Microsoft reference and conversation update
Goal: local Microsoft implementation coaching, retained chats, honest context readout and eccentric useful personality.
Constraints: offline runtime, owner-only downloads, no tenant operations, preserve current frozen release and auth/model/voice.
Inputs: official Microsoft Learn pages and local authored skills.
Outputs: pinned screened reference index, five shared Microsoft skills for IT/sysadmin, HUD meter, conversation continuity.
Approach: extend existing prompt registry and evidence pipeline; no cloud connector or new framework.
Meter: latest Ollama prompt/output token counts against configured 4096; not browser history size or a tokenizer estimate.
Validation: isolated Python tests, Node streaming UI tests, retrieval probes, unchanged MCP finding inventory, browser visual QA.
Release: stage, prepare with complete target inventory, activate with rollback retained.
Done: live local UI and grounded replies work, existing server remains available during preparation, docs report limits.

Compared approaches: new cloud connector/framework would add network and maintenance scope; extending current registry, evidence and NDJSON metadata needs only existing standard-library components. Choose the latter.

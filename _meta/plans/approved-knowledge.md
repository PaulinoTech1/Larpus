Goal: grounded local reasoning over role-approved archived research and kernel/platform/CPU documentation.
Constraints: no model internet, no new model tools, read-only sealed corpus, existing DLP/auth/CPU voice preserved, 4096-token model context.
Inputs: existing hash-pinned research PDFs and owner-reviewed publisher-only documentation URLs.
Outputs: vetted snapshot catalog, local SQLite FTS index, bounded cited excerpts injected as untrusted evidence, live offline verification.
Done when: requested platforms/CPUs and 2024-current kernel branches are locally indexed, six research roles retrieve scoped material, isolation and tests pass, server restored.
Approaches: (1) stuff entire documents into context: too large; (2) embedding model/vector service: extra weights/VRAM/processes; (3) standard-library SQLite FTS5: selected, CPU-only, no extra inference model.
Curation: exact official HTTPS hosts/URLs reviewed before HEAD and bounded GET; refuse redirects/executables/challenge pages; strip active HTML, scan extracted chunks, hash originals and index, retain rejected data inertly.
Scope: documents are reference evidence only; commands in documentation are never executed. Existing archives retain role restrictions. CPU public specifications do not reveal host inventory.
No commit or push requested in this turn. AgentDB command unavailable in this environment.

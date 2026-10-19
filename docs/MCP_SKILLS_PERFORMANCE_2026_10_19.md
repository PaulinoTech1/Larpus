# MCP Skills measurement — 2026-10-19

No chat speedup is established by this extension. It adds metadata/resource discovery,
not extra discovery calls to chat. Model selection, prompts, inference options, retrieval,
screening and CPU voice remain on the existing paths.

`scripts/benchmark_mcp_skills.py` is plan-only by default. `--run` compares prepared local
release IDs through the same fixed MCP executor, in alternating A/B order. Warmups are
excluded, failed attempts remain in denominators, missing stages are not zero and
p90/p95 use nearest rank. Private receipts retain answers, evidence and chunk arrival times.
An interrupted or identity-changing run cannot be a valid comparison. Answer quality
requires the existing rubric and supporting passages; citation identifiers alone do not prove it.

Standalone Windows validation timings and Linux/live results will be recorded separately.
Do not label standalone loader cost as an inference stage or compare candidate MCP timing
against baseline HTTP as a causal effect. Candidate HTTP/browser validation awaits activation.

Windows Python 3.10 standalone profile: ten measured trials after one excluded warmup.
Full-registry validation median was 185.184 ms (p95 190.401 ms); selected-prompt
validation median was 216.987 ms (p95 241.760 ms). Persona setup was outside the
selected-operation timer. These are descriptive host measurements, not isolated Linux
or end-to-end gains. The first profiler version also timed persona loading and is
retained as an invalid selected-operation comparison; it was not used to justify optimization.

No cross-request validation cache or optimization variant C has been adopted. Repeated
verification remains mandatory; a C candidate needs a measured, safe operation-local saving
and separate equivalence, tamper, review and prepared-release evidence.

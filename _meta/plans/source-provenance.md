# Source chronology and provenance
Goal: chronological source processing and explicit author/version provenance;
separate document authorship from quoted bibliography attribution.
Constraints: no network/model inference, no crash-workload restart, preserve
original sources and all saved notes, no commit/push, frozen releases immutable.
Inputs: reviewed research/catalog.json, knowledge catalogs/manifests and approved index.
Outputs: deterministic provenance sidecar, explicit reviewed relationships,
retrieval metadata/temporal policy, safe chronological queue and note audit.
Done when: metadata exported without inferred authors/dates; date/relationship
validation rejects bad links/cycles; source identity not derived from citations;
bibliography evidence labelled; existing notes audited without deletion; tests pass.
Choose a shared stdlib metadata module and checksum-bound sidecar, no index migration.
Reject LLM author extraction and automatic newer-means-correct heuristics.
Publication dates sort oldest first; unknown last, retrieval date never publication.
Supersedes/corrects links require scope and reviewed evidence; version forks coexist.
Keep note keys source+locator+text, record audit suspects separately, no blanket rebuild.
Contract: runtime provenance/knowledge/inference/security_scan, scripts provenance/
prepare-knowledge/study-notes/test-local, config source relationships, new tests/docs.

Validated:195 offline tests pass(two skips),7 provenance-focused tests pass;
HUD contracts pass; actual corpus retrieval attaches dates/authors, no inference.
Audit:30568 notes,1114 heuristic citation candidates, no deletion.

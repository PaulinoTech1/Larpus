# Complexity and failure accountability
Goal: track measured complexity/coupling, explain component interactions and
failure modes, retain useful cause chains instead of generic transport errors.
Constraints: local-only stdlib tools, no model/service restart or frozen edits;
DLP/privacy preserved, no owner prompts/secrets in diagnostic records, no commit.
Inputs: owned Python AST, authored component/failure catalog and boundary exceptions.
Outputs: bounded owner diagnostics, safe reference IDs, complexity baseline/gate,
ranked local report, dependency map and component value/failure ledger.
Done when: baseline regression makes configured test command fail loudly; causes
and frame locations survive MCP/voice/notes errors; redaction/bounds/protocol tests
pass; maps and limits are documented, all existing contracts preserved.
Choose stdlib AST + explicit budgets + structured stderr, no new services/deps.
Reject raw exception dumps (may contain secrets) and lines-of-code-only scoring.
Python function decisions/lines/import coupling measured, JS/PS complexity NOT CHECKED.
Record static imports versus dynamic IPC separately; no exhaustive failure claim.
Contract: runtime diagnostics/mcp_client/voice/inference/notes_worker, notes owner
script, minimal notes image, security scope, complexity CLI/config/catalog,
configured tests and new focused tests/docs. Staged-only until crash recovery.

Implementation: component ledger and import graph, explicit AST baseline gate in test-local, bounded stderr diagnostics and HUD correlation IDs. Validation: focused gate/privacy/protocol tests, full isolated suite and HUD scripts; no production activation or commit. See docs/COMPLEXITY.md for coverage limits.

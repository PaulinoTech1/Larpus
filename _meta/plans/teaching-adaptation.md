# Teaching profiles and experiment journal
Goal: owner-controlled evolution of teaching style per persona and selected skill.
Constraints: offline agent, no self-approval, no dependency/model/source-policy changes;
keep production available; preserve existing edits; no commit/push or activation.
Inputs: owner-selected bounded settings, rationale, success criteria and feedback.
Outputs: versioned accepted profiles, three-reply trials, review/accept/reject/restore,
browser-local journal and JSON export; fixed user-level model context.
Done when: trial lifecycle/rollback work, corruption/quota/conflicts preserve data,
chat/retrieval contracts pass and full Python/JS checks are reported honestly.
Choice: browser-local storage matching web/memory.js; no server-owned profile database.
Alternative: shared SQLite adds authenticated persistence API/migration scope.
Alternative: free-form self-edited system prompts enlarge authority and review scope.
Settings are enums; narrative journal text never enters inference context.
Profiles scoped to exact persona + skill; no automatic promotion or inferred learning.
Three completed replies end a trial; owner review decides promotion.
Model suggestions remain chat text; owner enters proposed settings explicitly.
Old HUD requests stay compatible; only new client wraps its last user question.
No AgentDB executable is available; use local repository contracts and this plan.

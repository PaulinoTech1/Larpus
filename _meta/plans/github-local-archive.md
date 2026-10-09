Goal: download all repositories owned by authenticated PaulinoTech1 and make their screened source/docs searchable by every Larpus persona.
Constraints: runtime stays offline with no credentials or GitHub tools; owner-side network only; keep production available; no execution of downloaded hooks/scripts, no push/commit; preserve previous snapshots and current working tree.
Inputs: authenticated owner inventory (22 connector-visible repos), native Git/GCM, existing FTS knowledge/DLP/input filters.
Outputs: ignored local full Git mirrors and commit-pinned default-branch file snapshots, audit manifest, filtered local reference index, owner refresh CLI and docs, staged activated release.
Done when: authenticated inventory complete/paginated, all repositories archived or failures explicit; verified object stores and source commits; secrets/injections excluded from index; retrieval across roles and live HUD chat verified; tests/scan/isolation gates pass.
Approaches: direct GitHub tools in MCP (violates offline boundary, reject); raw whole-repo model mount (exposes history/secrets/executable inputs, reject); owner mirrors + inert file snapshots + screened shared index (chosen; Git + Python stdlib).
Download all branches/tags/history; default-branch source is indexed within documented bounds. Submodules/LFS/releases/issues are distinct from Git object storage and reported rather than silently claimed downloaded.
Private originals and reports stay under ignored data/github. No repository instructions gain authority or are installed as skills.
AgentDB unavailable. No delegation. Existing build skill applied.

Completed: authenticated inventories agree on22, all mirrors fsck passed,19534
Windows files materialised;200 incompatible paths retained in mirrors. Screened
index7853 GitHub rows,247total documents,44034total passages. Every persona scoped
retrieval checked.97tests/UI/isolation/static gates pass;64clean skills/8retained
MCP warnings. Candidate and live gateway listed all22names and read README data.
Active1fb042ecf3a74d4ea4c0d4604d7a1534; previous1583267e031e49848cead54bf62035d0.
Private report/probe contents remain ignored data/github; public summary receipt
docs/GITHUB-ARCHIVE-VERIFICATION.json. No commit/push.

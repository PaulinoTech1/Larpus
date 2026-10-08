# Continuous local station health

The gateway starts a daemon health monitor automatically. It checks every 60 seconds
after the previous cycle completes; the authenticated HUD refreshes its health panel
every 30 seconds. Reports older than 180 seconds appear stale. No external reporting,
accounts or telemetry are configured. A slow first scan can delay the first report.

```powershell
python -m runtime.health
# Standalone monitoring when the gateway is not running:
python -m runtime.health --watch
```

Use one monitor per workspace. One-shot checks return nonzero for degraded/error
states. data/health/latest.json includes password setup, local skill hashes, a bounded
input-filter probe, actual SDK stdio tool discovery against config/mcp-approved.json,
installed model tags and GPU telemetry. In Windows Home isolated mode, health checks
real rootless/OCI configuration and repeats the network/file/quarantine denial probe.
Host developer mode remains explicitly unverified; a working MCP handshake alone
cannot prove internet isolation.
Missing password or Ollama is an error, never a healthy result.

## OWASP guidance and local scanner

[OWASP recommends NVIDIA SkillSpector](https://owasp.github.io/www-project-agentic-skills-top-10/skill-scanner-integration.html).
OWASP's own AST10 scanner is not published. Larpus uses SkillSpector 2.12.0,
source commit 3c8e4b958fda9602e0044885f766be0e49f03585, in static --no-llm mode.
Cloud/account-backed scanners are excluded. This is OWASP-recommended tooling,
not an OWASP certification or a comprehensive security audit.

Install the scanner separately during setup (Python 3.12–3.14; tested here on 3.14):

```powershell
py -3.14 -m venv vendor/skillspector-env
vendor/skillspector-env/Scripts/python.exe -m pip install -r requirements-scanner.txt
```

For an offline rebuild, prepare a wheel cache for this Python/platform and preserve
upstream licenses, then install with --no-index --find-links. The pinned source does
not pin all transitive dependencies. LARPUS_SCANNER_PYTHON can select the owner-installed
scanner interpreter. The scanner is not part of model inference.

Static mode alone can contact OSV for dependency checks. The fixed wrapper strips
credentials/proxy/tracing variables and denies Python socket/DNS and child execution
through an audit hook. A real subprocess test verifies socket denial. This is a
cooperative Python guard, not an OS sandbox against hostile native code. Semantic
LLM checks and live vulnerability-database checks are not claimed.

Changes to runtime, personas, registered skills, scanner wrapper, model policy or
MCP baselines trigger rescanning. Four skill directories and a generated export of
actual MCP descriptors plus fixed inference source files are scanned. The export's
config/mcp-capabilities.json declaration describes existing narrow scope; it grants
no permissions and does not change enforcement. Exact tool schema drift is checked
separately from static scanning. No credentials, recordings or conversations enter
scanner targets.

Canonical local reports are data/security/<target>.json and summary.json. Summary
binds results to an input fingerprint and scanner commit. Only complete, static-only,
zero-finding LOW reports pass; missing, changed, failed or incomplete evidence cannot
be clean. Inspect findings rather than widening capabilities to silence them.
Current checks are observational: warnings do not automatically stop the gateway.

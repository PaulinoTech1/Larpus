# Locally authored Larpus skills

Only project-authored prompt skills are accepted. There is no remote skill catalog,
URL importer, executable skill code or automatic installer. The initial skills are
home planning, IT interview practice, fictional character preparation and scenario
debriefing. Select one in the HUD; changing it clears conversation history.

Each skills/<id>/ folder contains only SKILL.md, with LF line endings and UTF-8
text. skills/registry.json records the slug, display metadata, local-authored origin
and SHA-256 of the exact bytes. Persona configs allowlist the skills they offer.
The loader rejects changed hashes, unknown folders, symlinks, additional files,
invalid metadata and suspicious filtered text; it repeats validation before chat.
The skill is appended to the server-owned system prompt. Browser text cannot
choose arbitrary paths or supply a system prompt. A hash detects drift, not authorship
or malicious intent: the owner must review each local change before repinning it.

To extend: write and review the local prompt, compute its byte hash with
Get-FileHash -Algorithm SHA256, add its registry entry, allowlist it in the desired
persona, run tests and the health scan, then inspect the JSON findings. Do not
copy an external skill into the registry and label it locally authored.
Skills guide coaching; they grant no shell, filesystem, browsing or MCP execution.

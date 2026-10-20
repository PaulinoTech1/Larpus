# Locally authored Larpus skills

The MCP Skills implementation publishes these reviewed files through
`io.modelcontextprotocol/skills` at revision `2026-07-28`: `skills/list`,
`skills/get` and standard `resources/read`. The canonical address is exactly
`skill://<registered-id>/SKILL.md`. These are protocol methods, not new tools.
Reading a file does not select it or append it to chat. The existing HUD/persona
allowlist still controls activation. See [acceptance status](MCP_SKILLS_ACCEPTANCE_2026_10_19.md)
for the distinction between implementation, preparation and production activation.

Entries carry the file's exact two-field frontmatter and a complete one-file
SHA-256/byte-size manifest. Only plain `name` and `description` scalars in the
reviewed format are supported; executable fields, ambiguous YAML and ancillary
files fail closed. Lists contain at most 16 entries per page. Each operation
freshly verifies the full local registry; cache hints are `ttlMs=0` and
`cacheScope=private`. Metadata freshness hints do not substitute for raw-byte verification.

A consuming host must bind approval to its own server identity **and** URI,
then verify the complete manifest, raw digest/size and frontmatter before use.
A same-named or same-URI skill from a different server has no local authority.

Only project-authored prompt skills are accepted. There is no remote skill catalog,
URL importer, executable skill code or automatic installer. The initial skills are
home planning, IT interview practice, fictional character preparation and scenario
debriefing. Each of the twelve personas now also offers five dedicated skills:
see the [role-specific catalog](ROLE_SKILLS.md). There are 60 specialist skills
and four preserved shared skills, plus five Microsoft implementation skills shared
by System Administrator and IT/Cybersecurity LARP Coach (69 registered total).
Select one in the HUD; changing it retains the chat and applies the new skill on
the next turn. Only the selected skill enters the model context. See
[Microsoft implementation and context controls](MICROSOFT_IMPLEMENTATION.md).

Each skills/<id>/ folder contains only SKILL.md, with LF line endings and UTF-8
text. skills/registry.json records the slug, display metadata, local-authored origin
and SHA-256 of the exact bytes. Persona configs allowlist the skills they offer.
The loader rejects changed hashes, unknown folders, symlinks, additional files,
invalid metadata and suspicious filtered text; it repeats validation before chat.
The registry accepts at most 128 skills; individual files remain bounded to
16,000 bytes and must pass the existing text filter. Persona allowlists still
limit which skills can be selected; increasing registry capacity grants no tools.
The skill is appended to the server-owned system prompt. Browser text cannot
choose arbitrary paths or supply a system prompt. A hash detects drift, not authorship
or malicious intent: the owner must review each local change before repinning it.

To extend: write and review the local prompt, compute its byte hash with
Get-FileHash -Algorithm SHA256, add its registry entry, allowlist it in the desired
persona, run tests and the health scan, then inspect the JSON findings. Do not
copy an external skill into the registry and label it locally authored.
Skills guide coaching; they grant no shell, filesystem, browsing or MCP execution.

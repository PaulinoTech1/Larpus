# Output DLP and owner quarantine

On Windows 11 Home, the isolated deployment keeps evidence in a dedicated Linux
volume mounted only into trusted MCP/DLP, never the model container. Use the
[Windows Home isolation guide](WINDOWS-HOME-ISOLATION.md) and its investigation
commands. The host ACL controls below describe development mode.

Every generated chat reply is staged as inert JSON in data/quarantine before
inspection, inside the inference service and before stdio MCP or HTTP returns.
Clean replies are deleted from staging before release. Held replies return only
a fixed message and random incident ID: no offending content, matched values,
system prompt, model tag or detailed reasons. Failed inspection, ACL setup,
storage, cleanup or a full quarantine withholds output. Oversized responses are
withheld without writing oversized evidence. Nothing streams around this gate.

Rules hold credential assignments/private keys, local paths, loopback/RFC1918 and
selected private IPv6 addresses, hidden controls, known project/home paths and
copied system-prompt lines of at least 40 characters. NFKC and whitespace-folded
comparison detect some formatting changes; known protected strings are also checked
in exact base64 and hex forms. config/dlp.json provides bounded limits and an owner
private-value list for noncredential identifiers. Never commit real secrets to that
tracked file. Credentials are not read from password records or environment variables
to populate a model prompt. The model still has no file/shell tools.

The quarantine directory has inherited access removed on Windows, with only the
current OS identity and SYSTEM granted access. POSIX uses owner-only directory/file
modes. Reparse-point/symlink targets are rejected. These are local filesystem controls,
not protection from administrators or a compromised process running as the same
owner. No separate service identity, container or OpenShell sandbox is installed
in this slice. The agent has no MCP read/release tool and the HTTP static server
serves only web/, never data/. An actual OS sandbox remains a deployment gate.

Investigation uses an owner-side terminal, never the HUD:

```powershell
python -m runtime.dlp list
python -m runtime.dlp inspect <32-character-incident-id>
python -m runtime.dlp delete <32-character-incident-id>
```

The inspector prints escaped JSON, not rendered HTML or executable output. Held
records contain full potentially sensitive text and reasons. A crashed/error scan
may leave a staged record for investigation. There is no automatic release command
or release API. No age-based automatic deletion: preserve evidence until reviewed;
the default capacity is 1024 records / 64 MiB, then fail closed. Clean deleted files
may remain recoverable on storage; deletion is not secure erasure. Quarantine is
ignored by Git and should be excluded from shared backups and file shares.

This applies to generated chat, not intentional authenticated administrative
metadata such as persona model selection and station health. It is deterministic
defense in depth, with false positives (for example a fictional private lab address)
and false negatives: paraphrases, split disclosures across responses, arbitrary
encoding, unknown secrets, and semantic inferences are not comprehensively detected.
Keep sensitive setup out of model context in the first place. It follows
[OWASP output-filtering guidance](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/)
without claiming disclosure immunity.

Continuous health checks validate policy, quarantine ACL setup and benign/credential
probes. Scanner fingerprints include the output gate, policy and ACL script. Health
warnings do not bypass the per-response fail-closed gate. Review ACLs and attempt a
second-identity read before asserting hostile-user isolation on a deployed host.

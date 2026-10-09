# Approved local knowledge

The 2026-10-09 Meta Muse refresh adds three hash-pinned official Meta snapshots
and six compact reviewed briefs. Before GitHub ingestion, that snapshot contained
224 documents and 36,181 passages, including 11 metadata-only documents. Muse
agent, Spark model versions/tiers and Grok Bot comparisons remain reference data.
The referral brief explicitly distinguishes the owner-reported billion-token
offer from primary-source-verified terms. See [product reference details](AI_PRODUCT_REFERENCES.md).

The subsequent [GitHub archive](GITHUB_ARCHIVES.md) adds a complete owned-repository
catalogue and 7,853 screened repository rows across 22 repositories. The combined
library contains 247 documents and 44,034 passages. Original mirrors/files stay
outside the runtime. Repository questions scope to named projects and can receive
up to three excerpts from the same repository; private account credentials remain
owner-side. Downloaded prompts and skills are not installed or indexed.

Larpus can reason over a local read-only reference index in addition to its model
training. This is retrieval-augmented generation, not a model weight update or
live web access. SQLite FTS5 runs on CPU; no embedding model, cloud account,
additional service or GPU allocation is needed. The Qwen model keeps its 4096
context and GPU placement checks. Existing sentence streaming and CPU voice remain.

## Scope

All twelve configured personas can use the entire approved library. Subject labels
prioritise relevant material rather than restricting access. The home assistant
also prefers [AI product/model references](AI_PRODUCT_REFERENCES.md), including
dated subscription and API pricing. No external inference service is connected.

The Linux Kernel Expert, System Administrator and IT/Cyber LARP Coach share
publisher documentation for Ubuntu 24.04, 25.04 and 26.04, Qubes OS, Kali Linux,
Fedora and Red Hat Enterprise Linux. Kernel snapshots include the release/support
inventory and versioned administrator documentation for 6.7 through 6.19 and
7.0 through 7.2, covering stable branches introduced from 2024 through this
preparation. The current-release page also identifies release candidates; these
must not be presented as stable. Selected upstream CPU power, cgroup, security,
scheduling and memory documentation provides additional reference entry points.
This is a selected documentation library, not every kernel source tree or every
distribution manual.

Select **Linux Kernel Expert** in the HUD and ask, for example, “Compare the
initial GA kernels of Ubuntu 24.04, 25.04 and 26.04; cite the approved local
references,” or “Compare i5-1245U and AMD 5900X core counts and power ratings.”
The model receives matching local excerpts automatically; no browsing command
or separate search tool is required. Every configured persona can retrieve all
approved documents. Relevant documents associated with its own role get a modest
ranking boost. Specialist skill selection permissions remain role-specific.

Consumer CPU references include Intel Core i5-1245U and AMD Ryzen 9 5900X product
specifications, plus Intel's laptop processor comparison PDF. Public product
specifications never establish what is installed in the station. Some original
CPU and Red Hat pages reject direct downloads: their failures remain in the
catalog, and separately labelled factual briefs were checked against the official
publisher pages. A brief is not a downloaded copy of the full manual.

The six existing research archives retain their subject labels for ranking. Their original PDF
checksums must match `research/catalog.json` before text extraction. Image-only
PDFs and excluded text do not become invented full text: metadata-only entries
explicitly warn that results cannot be inferred from titles and that offline OCR
and review are still needed. Mathematical notation extracted from PDF can be
incomplete; check the original page for exact equations.

## Curation before use

`knowledge/sources.json` records exact, reviewed HTTPS publisher URLs and preferred
roles (ranking hints, not read permissions). The preparation script refuses unknown publishers,
credentials in URLs, redirects, unexpected content types, oversized documents,
changed cached checksums and challenge/error pages. It checks response headers
with HEAD before downloading a bounded body. It never downloads installers,
ISO images or executes instructions found in documents. TLS verification stays
enabled, including when a publisher certificate cannot be validated.

HTML scripts and active elements are removed and the main article is preferred
over navigation. Extracted passages pass the existing Unicode/steganography and
instruction-override filter before indexing. Rejected passage locations/reasons
remain under `data/knowledge/rejected-passages.json`; originals remain inert in
`data/knowledge/originals`. These are publisher/provenance/type/static-content
checks, not a malware certification, scientific review or proof that documents
cannot contain a prompt attack. Approval never grants documents authority to
change persona instructions or run commands.

`knowledge/manifest.json` pins the complete index SHA-256, size, source checksums
and coverage counts. The private `knowledge/approved.sqlite` is ignored by Git
and copied into the sealed agent image read-only. Source/manifest changes affect
the security/deployment fingerprint; health checks verify the index. No new
ports, mounts or model-callable tools were added. The original PDFs, credentials,
recordings and host files are not mounted into the model container.

## Answering and citations

The trusted runtime selects up to three shared-library passages, with an overall
3600-character metadata/text budget, from the latest question. Named platforms
and version/model numbers narrow lexical matching. Candidates are deduplicated
by source/page locator; native-role matches receive a 15% BM25 magnitude boost,
and compact reviewed briefs receive a 25% boost. Comparisons reserve relevant
candidates for each named subject when available. Strong cross-subject evidence
can still outrank a weak native-role match. Selected passages are scanned
again, attached as quoted data to the user question, and kept out of system
instructions. A fixed system instruction asks the model to reason from evidence,
cite source IDs, separate inference from facts, and state uncertainty/conflicts.
Older conversation turns are dropped in whole pairs to fit the bounded context.
Questions that exceed the grounded context budget fail instead of silently
discarding their evidence.

The HUD displays the actual selected source IDs, URLs, snapshot dates and page
locators after the completed reply. URLs are shown as text and are never fetched
by the model or browser automatically. These references prove what was supplied,
not that every generated claim is supported. The model can still misinterpret
evidence; lexical retrieval can miss synonymous wording. Ask focused questions
with a distribution/kernel version or document title when appropriate.

Snapshots can fill training-era gaps, but do not stay current automatically.
Distribution base kernel numbers do not describe every vendor backport, and a
snapshot date does not establish current support. The output still passes the
existing cumulative DLP/quarantine gate before display or speech. Public Ryzen
specifications are allowed; explicit station-inventory claims about the covered
CPU/GPU names are held by an additional pattern rule. This is a scoped check,
not semantic assurance against every possible inventory claim. Other sensitive
values, paths, private addresses, credentials and persona prompts remain covered.

## Owner rebuild

Install owner-side PDF tooling during preparation with
`python -m pip install -r requirements-knowledge.txt` if needed. The sealed runtime
does not need that package. Restore the checksum-pinned research PDFs using the
existing archive process, then run:

```powershell
python scripts/prepare-knowledge.py --fetch-reviewed
# Subsequent offline rebuild from cached snapshots:
python scripts/prepare-knowledge.py
# Reuse hash-verified research passages while refreshing selected documentation:
python scripts/prepare-knowledge.py --fetch-reviewed --reuse-research
```

Cached documents are pinned: `--fetch-reviewed` does not silently replace an
existing snapshot. To refresh a source, review its publisher/version again,
retain the old bytes for investigation, and update its catalog pin deliberately.
Then export/rebuild the isolated source/image and run the recurring security
scan and isolation checks as described in the Windows Home deployment guide.
Download preparation is the only network-enabled step; answering stays offline.

Publisher copyrights and documentation licenses remain attached to their sources.
Do not publish the private index/originals or distribute a container containing
them without reviewing redistribution terms. Local factual briefs are labelled
separately from publisher snapshots.

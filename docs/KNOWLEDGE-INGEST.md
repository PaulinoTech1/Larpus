# Knowledge ingest: OCR sidecars, page limit, control normalization and reviewed hashes

Written 2026-11-01. This covers the owner-approved ingest changes of
2026-10-29 to 2026-10-31. The index they produced went live in data-only release
[`b788d9fd`](releases/RELEASE-b788d9fd-2026-11-01.md). Decision entries are in
[DECISIONS.md](DECISIONS.md), dated 2026-10-29 6:51 PM, 2026-10-30 10:25 AM and
2026-10-31 5:50 AM ET.

Code: `scripts/prepare-knowledge.py` and `runtime/reference_review.py`.
Catalog: `research/catalog.json`.
Allowlist: `config/reference-reviews.json`.
Tests: `tests/test_knowledge_preparation.py`.

## 1. OCR sidecars for the 29 MIT 18.330 scans

The `mit-18330-01` to `mit-18330-29` handouts (18.330 Introduction to
Numerical Analysis, Toomre 2004, MIT OCW) are image-only PDFs. Until Oct 30
each one was indexed as a single metadata-only row.

- **Engine.** The built-in Windows 11 `Windows.Media.Ocr` (en-US, on-device)
  ran on pages rendered at 300 dpi with the existing PyMuPDF 1.28.2. It used
  the CPU only, and nothing was downloaded or installed. Output: 29 files,
  49 pages, 54,315 characters.
- **Sidecar format.** `data/research/<role>/<level>/<id>.ocr.txt` holds raw
  engine text under `[page N]` headers. `prepare-knowledge.py` reads it as
  `text/x-larpus-ocr-pages`, with locators `ocr page N`.
- **Hash-pinned.** Each catalog entry carries `ocr_sha256`. The build checks
  the PDF's own `sha256` first and then the sidecar hash, and stops on any
  mismatch. **OCR never runs at build time.**
- **Quality.** Prose is good. Equations are unreliable: subscripts,
  superscripts and operators are lost, and o/0, l/1 and B/8 get confused.
  The text works for search and concept-level notes. Exact formulas and
  numbers quoted from these handouts must be checked against the page.
  `mit-18330-15` is a plot and stays metadata-only.
- **Result.** 28 of the 29 handouts have text passages (82 in total, 1 to 5
  each).

## 2. PDF page limit raised from 700 to 1000

`extracted_pdf()` now rejects PDFs over **1000** pages instead of 700 (owner
approval 2026-10-30 10:09 AM ET: "Also raise the page limit and add the 4 big
textbooks"). These books had been metadata-only under the old limit:

- `boyd-convex-optimization`
- `strang-calculus`
- `nemirovski-modern-convex-optimization`
- `driver-analysis-tools`

`keisler-elementary-calculus` (about 990 pages, mostly image-only) also
crossed the limit and gave 7 passages. The password and extraction-permission
check is unchanged, and `upf-96ebbf0a` stays excluded because its PDF forbids
extraction.

## 3. Control-character normalization for the 4 textbooks

The local text screen held many textbook passages as `hidden_control` or
`unicode_carrier_or_incomplete_scan`. The cause was PDF font-encoding debris.
None of them was held for injection, role spoofing, DLP or secrets.

- **Catalog flag.** `text_normalization: "pdf-control-format-to-fffd-v1"` is
  set on the four textbooks above, and on no other source. The build rejects
  any other value, and it also rejects the flag on a source that is not a PDF.
- **Rule.** `normalized_pdf_text()` replaces each C0/C1 control character
  (category Cc, except tab, LF, CR and form feed) and each invisible format
  character (Cf) with U+FFFD, one for one. Offsets do not move, and passages
  without such characters stay byte-identical. **The ordinary screen still
  runs on the normalized text.**
- **Re-parsing.** Flagged sources are always parsed again, even with
  `--reuse-research`.
- **Recovered.** 1,566 passages: Strang 1,249 and Driver 317.
- **Characters replaced.**
  - Strang: about 8,500 occurrences, mostly U+0012, U+0081 and U+0019.
  - Driver: U+0012, 2,341 times.
  - No Cf characters were present.

## 4. Per-book hash allowlist for Greek-letter false positives

Normalization cannot help with 503 passages that were held only because
stegdetect flags Greek math letters (nu, tau, alpha, rho, chi, zeta, kappa) as
mixed-script homoglyphs (`unicode.mixed_script.v1`). Rewriting those letters
would change the mathematics.

- **How it works.** `config/reference-reviews.json` lists the exact SHA-256 of
  each reviewed passage under its own source id: Driver 241, Nemirovski 139
  and Boyd 123. This follows the earlier `chicone` and `salsa` entries of
  2026-10-14. `inspect_reference(part, source_id)` accepts a passage only if
  its hash is listed for that same source id. Every other passage goes
  through the ordinary `inspect_message` screen.
- **Review of each passage.** Before a hash was listed, the passage was checked
  for all of the following:
  - a complete scan with no text transformation;
  - only mixed-script findings, all on Greek code points;
  - no control, format, combining-run, instruction or role-spoof hit.
- **Scope.** The screen is **not** disabled or bypassed globally. The
  instruction and role-spoof rules still apply, and a hash is not accepted
  under any other source id.
- **Result.** None of the 2,069 recovered passages (1,566 normalized plus 503
  allowlisted) is still blocked. Index: 88,201 -> 90,270 passages. Embeddings:
  86,122 -> 88,191 rows, with the new ones embedded on CPU.
- **Reuse mode.** In reuse mode, earlier rows in `rejected-passages.json` are
  kept only for reused sources. This dropped the stale "PDF exceeds page
  limit" rows (11,041 -> 8,843 rows).

## 5. Warning: `knowledge/manifest.json` is close to the 100,000-byte limit

`runtime/knowledge.py` rejects a knowledge manifest larger than **100,000
bytes** (`manifest.stat().st_size>100000`). It applies the same limit to the
notes manifest.

| Copy of `knowledge/manifest.json` | Size |
| --- | --- |
| Git blob (LF) | 96,485 bytes |
| Windows checkout and release `b788d9fd` (CRLF, 2,956 lines) | **99,441 bytes**, 559 bytes of headroom |

A handful of new sources, or a rebuild that writes CRLF and adds a few lines,
will push the manifest past the limit, and retrieval will then fail with
`Invalid knowledge manifest`. Before the next ingest, the owner should choose
one of these:

- raise the limit in a reviewed code change;
- write the manifest compactly or with LF line endings;
- move per-source detail out of the manifest.

Nothing has been changed yet.

## Not in git

Downloaded PDFs, OCR sidecars, `knowledge/*.sqlite`, `*.npy`, the embeddings
and notes manifests, and release tars stay in ignored paths on the owner's PC,
as `.gitignore` requires. Git tracks only the catalog, the manifest, authors,
the reviewed hash allowlist and the code.

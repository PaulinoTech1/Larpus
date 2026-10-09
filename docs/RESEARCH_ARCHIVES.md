# Local persona research archives

Prepared 2026-10-08 for personal, offline study. The six catalogs each contain
**10 undergraduate dissertations/capstone reports, 8 master's theses, and 7
doctoral theses**. Undergraduate entries are actual student submissions rather
than ordinary conference or journal papers. Joint bachelor/master submissions
are labeled and counted once. Degrees need not be in a department with the same
name as the persona: applied continuous mathematics, for example, includes
engineering and physics theses about differential equations.

The current build is **complete**: all 150 student PDFs and eight supplementary
cryptography references are downloaded. MIT's repository initially required
human verification; downloads resumed after the owner completed the browser
check. No challenge was bypassed. Each PDF has a pinned SHA-256 digest and size.

| Persona archive | Undergraduate / master's / doctoral catalog | Student PDFs available |
| --- | --- | --- |
| Cryptography | 10 / 8 / 7 | 25 / 25 |
| IT / Cybersecurity LARP | 10 / 8 / 7 | 25 / 25 |
| Continuous Mathematics | 10 / 8 / 7 | 25 / 25 |
| Quantum Physics | 10 / 8 / 7 | 25 / 25 |
| Statistics | 10 / 8 / 7 | 25 / 25 |
| Enterprise Systems Administration | 10 / 8 / 7 | 25 / 25 |

## Where the archives live

Open `data/research/INDEX.md` for the local library. Each persona directory has
an `INDEX.md`, `manifest.json`, and degree-level PDF folders. Six ZIP packages
live in `data/research/archives/`; their manifests identify actual availability.
`data/research/verification.json` records the actual completeness, hashes,
package checks, and pending IDs. `data/research/pdf-inspection.json` records PDF
parsing and title-page text checks.

The repository contains the rebuildable [catalog](../research/catalog.json),
the readable [source list](../research/CATALOG.md), and the owner-run
[archive script](../scripts/research-archive.py). Full documents and packages
remain under ignored `data/`; they are not included in Git or published by the
gateway. Preparation added no ports, container mounts, model changes, or
runtime network access.

## Scope and sources

- **Cryptography:** public-key foundations, secret sharing, threshold protocols,
  signature security, ECC, AES, verification, embedded hardware, and side
  channels. Undergraduate reports add AES implementation tampering, FourQ
  side-channel evaluation, NTT optimization, and Kyber/Dilithium implementation.
- **IT/Cybersecurity:** authentication, access control, secure storage, intrusion
  evaluation, formal security APIs, memory defenses, critical infrastructure,
  adversarial LLM prompts, Kubernetes assessment and detection, and maritime
  threat modeling.
- **Continuous mathematics:** integration, Fourier analysis, manifolds,
  functional/operator analysis, calculus of variations, ODEs, PDEs, stochastic
  differential equations, conformal mapping, numerical methods, and error
  bounds. Discrete-mathematics theses were excluded.
- **Statistics:** Bayesian and causal inference, dependent data, regression,
  time series, uncertainty, missing data, privacy, and applied statistical
  measurement.
- **Enterprise administration:** NetApp clustered storage, deduplication,
  distributed storage, OLTP transactions, DNS resilience, fault tolerance,
  crash-safe filesystems, virtualization, Kubernetes capacity, orchestration,
  data-center servers, and cloud workload placement. Historical architectures
  are foundational readings rather than current enterprise runbooks.
- **Quantum physics:** quantum foundations, spinors, perturbation theory,
  phase space, quantum field theory, optics, entanglement, decoherence,
  Hamiltonian engineering, and many-body simulation.

Sources are MIT's university repository, Radboud University's official bachelor
thesis collection, and Universitat Pompeu Fabra's original bachelor report.
Records include authors, year, institution/program where available, exact degree
metadata, degree evidence, language, topics, rights, and primary source URLs.
Several historical PDFs are scans without usable title-page text; their degree
evidence remains the university record. Three conflicting MIT degree tags were
resolved against original title pages and classified as master's submissions.
No scientific correctness or peer-review endorsement is implied by inclusion.

## Additional cryptography references

Eight primary references sit outside the 25 student-work quota:

| Reference | Purpose |
| --- | --- |
| [FIPS 197, updated 2023](https://csrc.nist.gov/pubs/fips/197/final) | AES primitive and key schedules |
| [SP 800-186](https://csrc.nist.gov/pubs/sp/800/186/final) | ECC domain parameters |
| [FIPS 203](https://csrc.nist.gov/pubs/fips/203/final) | Exact standardized ML-KEM |
| [FIPS 204](https://csrc.nist.gov/pubs/fips/204/final) | Exact standardized ML-DSA |
| [SP 800-227](https://csrc.nist.gov/pubs/sp/800/227/final) | Secure implementation and use of KEMs |
| [SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final) | GCM/GMAC, IV uniqueness and authentication |
| [CRYSTALS-Kyber specification v3.02](https://pq-crystals.org/kyber/resources.shtml) | Historical design and security rationale |
| [CRYSTALS-Dilithium specification v3.1](https://pq-crystals.org/dilithium/resources.shtml) | Historical design and signature rationale |

Kyber/Dilithium candidate specifications are not interchangeable with FIPS
203/204. NIST's SP 800-186, FIPS 203, and FIPS 204 pages list potential
updates/errata; the catalog flags these. SP 800-38D has a planned revision.
Before implementation, consult the official publication status and errata;
the offline PDFs are pinned snapshots, not an automatically updated standards
service. Implementation readings address memory, CPU/vectorization, power,
latency, masking, side channels, verified arithmetic, and parameter selection.

## Rebuild and verification

Run from the repository in Windows PowerShell:

```powershell
# Explicit online preparation on the owner's host. Does not run inside MCP.
python scripts/research-archive.py fetch

# Strict offline verification and packaging require every PDF.
python scripts/research-archive.py verify
python scripts/research-archive.py pack

# Optional recovery mode: report missing files instead of claiming completion.
python scripts/research-archive.py verify --allow-missing
python scripts/research-archive.py pack --allow-missing
```

An entry with an existing pinned checksum must match it; a changed local or
remote PDF is retained for investigation and rejected. The downloader uses
HTTPS with certificate validation, a 128 MiB limit per PDF, bounded retries,
and stops new requests to a host that returns access denial or a human
verification challenge. It does not solve CAPTCHAs, use external accounts, or
silently replace a changed document.

For pending records, obtain the original through the primary source's normal
browser flow and save it to the exact location listed by its ID and level in
the catalog. After reviewing the source and title page, the explicit owner
curation command can record its initial checksum:

```powershell
python scripts/research-archive.py fetch --id <catalog-id> --record-hashes
```

If the local PDF already exists, that command records its hash without a network
request. Existing pinned hashes are never overwritten by `--record-hashes`.
The catalog deliberately has no invented hash for a missing PDF. Preserve the
updated catalog when backing up a completed collection. Verification and ZIP
creation use the Python standard library; one-time PDF structure/text inspection
used `pypdf==6.19.0` on the owner host, without modifying the original files.

`data/research/pending-downloads.csv` lists each remaining source, original
repository filename, and exact local destination. If browser downloads retain
the repository's original filenames, the owner can copy those specific files
into the archive and record their initial hashes without deleting the Downloads
copies:

```powershell
python scripts/research-archive.py fetch --record-hashes --import-dir "$env:USERPROFILE\Downloads"
```

This checks only the catalog's exact PDF filenames. Other Downloads files are
not imported. Review newly imported title pages before considering their degree
classification final. A browser verification cookie may not be available to
the host's Python HTTP client; browser downloads/import remain a supported way
to obtain the remaining originals through the repository's normal access flow.

## Rights and the agent boundary

Original author/publisher rights remain in force. MIT records explicitly
restrict reproduction/distribution without permission; public viewing does not
grant a blanket redistribution license. Keep this owner-directed study library
private. Do not add downloaded theses or archive ZIPs to the public GitHub repo.
The Larpus source license does not relicense these documents.

These archives are reference material, not locally authored skills. No report
is installed as a skill, appended to a persona system prompt, or exposed as a
new MCP operation. The isolated model cannot browse these directories or the
internet. The output-DLP quarantine retains its separate investigation purpose.

Any future retrieval integration must treat extracted passages as untrusted
source data, preserve citations, use bounded read-only access, and pass through
the existing input/output controls. Downloaded PDF code, commands, links and
embedded actions must not become tool instructions. The current validation
proves PDF structure/readability where inspected, checksum consistency,
unique downloaded student documents, ZIP integrity, and catalog counts; it
does not establish a full malware scan or prompt-injection immunity.

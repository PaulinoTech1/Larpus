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
live web access. SQLite FTS5 runs on CPU. Since 2026-10-09 an optional CPU-only
semantic tier (pinned bge-small embeddings and a bge-reranker-base cross-encoder,
see below) reorders candidates; no cloud account, additional service or GPU
allocation is needed. The Qwen model keeps its 131072-token
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

The 2024 peer-reviewed [habit-formation systematic review](https://www.mdpi.com/2227-9032/12/23/2488/notes)
is indexed from Europe PMC's CC BY 4.0 full-text XML for the psychologist and
home-assistant roles. Its 62 screened passages include the abstract and article
body, excluding the reference list. It studies health behaviours and reports
substantial variation in the time to automaticity; LARPUS should not promise a
fixed number of days or generalise its timing estimates to every kind of habit.
The article is evidence for answering questions, not a clinical treatment
protocol or proof that LARPUS changes a user's behaviour.

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

## Vetted-source rule for research files (2026-10-09)

Only reviewed, pinned material may enter the AI-readable library. Web documents
already pass the `prepare-knowledge.py` publisher allowlist. Research PDFs now
pass `scripts/research_policy.py` in both `research-archive.py` (catalog
load) and `prepare-knowledge.py` (before any text extraction):

- Source, download and degree-evidence URLs must be plain HTTPS on the reviewed
  host list: university repositories (MIT, Caltech, UPF, Radboud), NIST, the
  CRYSTALS authors' site and Mathematical Sciences Publishers; since 2026-10-10
  also the university repositories and mathematics department/faculty hosts of
  Cambridge, Imperial, Georgia Tech, Utrecht, ETH Zurich, MIT (OCW and math.mit.edu),
  Harvard, Wisconsin-Madison, Cornell, Princeton, Stanford, UC San Diego, UC Davis,
  Chicago, Brown, Colorado State, Vienna and Whitman College. DOI and handle
  resolvers are not allowlisted; records use the repository's own URL.
- Title, authors, year and a rights statement are required; student works need
  degree evidence.
- Downloaded text must have a pinned SHA-256 and byte size; files whose bytes
  differ are refused, and PDFs not listed in the catalog are never indexed.
- Every extracted passage still passes the Unicode/steganography and
  instruction-override filter; rejects are logged, not indexed.

Adding a new publisher means adding it to `RESEARCH_HOSTS` with a comment
explaining why it is trustworthy, in a reviewed change. Personal pages, mirrors,
aggregators (for example scispace) and anti-bot workarounds are not acceptable
sources. `tests/test_research_policy.py` covers the refusals.

## CPU semantic tier (2026-10-09)

`knowledge/embeddings.npy` holds bge-small-en-v1.5 vectors (title + passage, CLS,
L2-normalised, float16) for 43,549 unique approved passages; `embeddings-rowids.npy`
maps them to `approved.sqlite` rows. `embeddings-manifest.json` pins both files by
SHA-256 and the exact database hash and embedder revision; a mismatch disables the
tier and BM25 continues unchanged. The tier only ranks already-approved passages:
it adds no documents, and every selected passage still passes the input filter.
Owner rebuild, after `prepare-knowledge.py`:

    python scripts/prepare-retrieval.py verify
    python scripts/prepare-retrieval.py index

The first build took 47 minutes on 6 CPU workers while the GPU notes job was running.
Models, wheels and their hashes are listed in `config/cpu-retrieval.json`.

## Mathematician sources added 2026-10-10

Owner-approved on 2026-10-10 and hash-pinned in `research/catalog.json` (role `mathematician`).
Five doctoral theses count toward the role quota (phd 7 -> 12); textbooks and course notes are
uncounted `references` with their teaching level kept in `course_level`.

`training_use` marks whether an entry may enter shareable fine-tuning data: `allowed` (explicit
licence or author permission) or `private-only` (no explicit licence; local offline study and
retrieval only). Entries without the field are treated as not cleared. Exporters must keep only
`allowed` entries.

- `strang-calculus` - Calculus (3rd ed.) (Strang, Gilbert, 2017; MIT OpenCourseWare); level `references`; training_use `allowed`.
- `guichard-calculus` - Calculus (Early Transcendentals, single & multivariable) (Guichard, David, 2023; Whitman College); level `references`; training_use `allowed`.
- `keisler-elementary-calculus` - Elementary Calculus: An Infinitesimal Approach (online ed.) (Keisler, H. Jerome, 2026; University of Wisconsin-Madison); level `references`; training_use `allowed`.
- `loomis-sternberg-advanced-calculus` - Advanced Calculus (revised ed.) (Loomis, Lynn H.; Sternberg, Shlomo, 1990; Harvard University); level `references`; training_use `allowed`.
- `mit-18s096-matrix-calculus` - Matrix Calculus (for Machine Learning and Beyond) - full lecture notes (Edelman, Alan; Johnson, Steven G., 2023; MIT OpenCourseWare); level `references`; training_use `allowed`.
- `mit-18100a-real-analysis` - 18.100A Real Analysis: Complete Lecture Notes (Rodriguez, Casey, 2020; MIT OpenCourseWare); level `references`; training_use `allowed`.
- `mit-18100b-real-analysis` - 18.100B Real Analysis: Full Lecture Notes (Colding, Tobias Holck, 2025; MIT OpenCourseWare); level `references`; training_use `allowed`.
- `sternberg-real-variable` - Theory of Functions of a Real Variable (Sternberg, Shlomo, 2005; Harvard University); level `references`; training_use `allowed`.
- `hunter-measure-theory` - Measure Theory (lecture notes) (Hunter, John K., 2011; University of California, Davis); level `references`; training_use `private-only`.
- `driver-analysis-tools` - Analysis Tools with Applications (lecture notes) (Driver, Bruce K., 2003; University of California, San Diego); level `references`; training_use `private-only`.
- `melrose-functional-analysis` - Functional Analysis: Lecture Notes for 18.102 (Melrose, Richard, 2020; MIT OpenCourseWare); level `references`; training_use `allowed`.
- `teschl-schroedinger-operators` - Mathematical Methods in Quantum Mechanics: With Applications to Schroedinger Operators (Teschl, Gerald, 2014; University of Vienna); level `references`; training_use `allowed`.
- `miller-1803-ode-notes` - 18.03 Differential Equations: Supplementary Notes (Miller, Haynes R., 2010; MIT OpenCourseWare); level `references`; training_use `allowed`.
- `teschl-ode-dynamical-systems` - Ordinary Differential Equations and Dynamical Systems (Teschl, Gerald, 2012; University of Vienna); level `references`; training_use `allowed`.
- `hunter-pde-notes` - Notes on Partial Differential Equations (Hunter, John K., 2014; University of California, Davis); level `references`; training_use `private-only`.
- `dunkel-1804-complex-analysis` - 18.04 Complex Analysis with Applications (lecture notes, adapted from J. Orloff) (Dunkel, Joern; Orloff, Jeremy, 2019; Massachusetts Institute of Technology); level `references`; training_use `private-only`.
- `princeton-mat330-complex-analysis` - Complex Analysis with Applications: MAT330 Lecture Notes (Shapiro, Jacob, 2024; Princeton University); level `references`; training_use `private-only`.
- `boyd-convex-optimization` - Convex Optimization (Boyd, Stephen; Vandenberghe, Lieven, 2004; Stanford University); level `references`; training_use `allowed`.
- `nemirovski-modern-convex-optimization` - Lectures on Modern Convex Optimization (lecture notes, 2023) (Ben-Tal, Aharon; Nemirovski, Arkadi, 2023; Georgia Institute of Technology); level `references`; training_use `private-only`.
- `han-2024-spde-random-operators` - Coupling in SPDEs and spectral analysis of heavy-tailed random operators (Han, Yi, 2024; University of Cambridge); level `phd`; training_use `allowed`.
- `turner-2025-unparameterised-path-space` - Functions on unparameterised path space (Turner, William F., 2025; Imperial College London); level `phd`; training_use `allowed`.
- `sujanani-2024-first-order-methods` - Fast First-Order Methods for Large-Scale Nonconvex Optimization and Semidefinite Programming (Sujanani, Arnesh M., 2024; Georgia Institute of Technology); level `phd`; training_use `allowed`.
- `cherney-denton-thomas-waldron-linear-algebra` - Linear Algebra (Cherney, David; Denton, Tom; Thomas, Rohit; Waldron, Andrew, 2013; University of California, Davis); level `references`; training_use `allowed`.
- `treil-linear-algebra-done-wrong` - Linear Algebra Done Wrong (Treil, Sergei, 2017; Brown University); level `references`; training_use `allowed`.
- `boyd-vandenberghe-vmls` - Introduction to Applied Linear Algebra: Vectors, Matrices, and Least Squares (Boyd, Stephen; Vandenberghe, Lieven, 2018; Stanford University); level `references`; training_use `allowed`.
- `lankham-nachtergaele-schilling-linear-algebra` - Linear Algebra As an Introduction to Abstract Mathematics (MAT67 notes) (Lankham, Isaiah; Nachtergaele, Bruno; Schilling, Anne, 2016; University of California, Davis); level `references`; training_use `allowed`.
- `margalit-rabinoff-interactive-linear-algebra` - Interactive Linear Algebra (Margalit, Dan; Rabinoff, Joseph, 2019; Georgia Institute of Technology); level `references`; training_use `allowed`.
- `strang-zoomnotes-linear-algebra` - ZoomNotes for Linear Algebra (Strang, Gilbert, 2021; MIT OpenCourseWare); level `references`; training_use `allowed`.
- `hatcher-algebraic-topology` - Algebraic Topology (Hatcher, Allen, 2002; Cornell University); level `references`; training_use `allowed`.
- `hatcher-vector-bundles-k-theory` - Vector Bundles and K-Theory (v2.2) (Hatcher, Allen, 2017; Cornell University); level `references`; training_use `allowed`.
- `hatcher-point-set-topology-notes` - Notes on Introductory Point-Set Topology (Hatcher, Allen, 2005; Cornell University); level `references`; training_use `private-only`.
- `hatcher-3-manifolds` - Notes on Basic 3-Manifold Topology (Hatcher, Allen, 2007; Cornell University); level `references`; training_use `private-only`.
- `miller-18905-algebraic-topology` - Lectures on Algebraic Topology (18.905) (Miller, Haynes, 2016; MIT OpenCourseWare); level `references`; training_use `allowed`.
- `may-concise-algebraic-topology` - A Concise Course in Algebraic Topology (May, J. P., 1999; University of Chicago); level `references`; training_use `private-only`.
- `cavalieri-math490-topology` - Introduction to Topology (Math 490 course notes) (Cavalieri, Renzo; students), et al. (Math 490, 2010; Colorado State University); level `references`; training_use `private-only`.
- `shi-2023-unstable-periodic-homotopy` - Unstable Periodic Homotopy Theory (Shi, Yuqing, 2023; Utrecht University); level `phd`; training_use `allowed`.
- `appenzeller-2024-affine-buildings` - Semialgebraic groups and generalized affine buildings (Appenzeller, Raphael, 2024; ETH Zurich); level `phd`; training_use `allowed`.

## Linux kernel expert sources added 2026-10-10

Owner-approved on 2026-10-10 and hash-pinned in `research/catalog.json` (role `linux-kernel-expert`,
`ROLE_QUOTA` phd 5). 12 PDFs and 27 official HTML pages. HTML entries carry `"format": "html"`:
the page is stored byte-exact as `data/research/<role>/<level>/<id>.html`, SHA-256/byte pinned and
vetted like a PDF, and indexed with the same HTML main-text extractor used for web sources (no
script execution, no fetch). `vet()` accepts only `pdf` or `html`. The same `training_use` rule applies.

- `nist-sp-800-125` - NIST SP 800-125 Guide to Security for Full Virtualization Technologies (NIST, 2011); pdf; level `references`; training_use `allowed`.
- `nist-sp-800-125a-r1` - NIST SP 800-125A Rev.1 Security Recommendations for Server-based Hypervisor Platforms (NIST, 2018); pdf; level `references`; training_use `allowed`.
- `nist-sp-800-125b` - NIST SP 800-125B Secure Virtual Network Configuration for VM Protection (NIST, 2016); pdf; level `references`; training_use `allowed`.
- `nist-sp-800-123` - NIST SP 800-123 Guide to General Server Security (NIST, 2008); pdf; level `references`; training_use `allowed`.
- `nist-sp-800-190` - NIST SP 800-190 Application Container Security Guide (NIST, 2017); pdf; level `references`; training_use `allowed`.
- `qubes-arch-spec` - Qubes OS Architecture (v0.3) (Rutkowska, Joanna; Wojtczuk, Rafal; Invisible Things Lab, 2010); pdf; level `references`; training_use `private-only`.
- `qubes-security` - Qubes OS project security center (Qubes OS Project, 2026); html; level `references`; training_use `allowed`.
- `qubes-security-bulletins` - Qubes security bulletins (QSBs) index (Qubes OS Project, 2026); html; level `references`; training_use `allowed`.
- `qubes-security-design-goals` - Qubes OS security design goals (Qubes OS Project, 2026); html; level `references`; training_use `allowed`.
- `ubuntu-security-features` - Ubuntu security features (Canonical, 2026); html; level `references`; training_use `private-only`.
- `arch-wiki-security` - Security - ArchWiki (Arch Linux community, 2026); html; level `references`; training_use `allowed`.
- `kali-docs-policy` - Kali Linux Documentation - Policy (incl. network service, update, root policies) (OffSec / Kali Linux, 2026); html; level `references`; training_use `private-only`.
- `mint-verify-iso` - Linux Mint Installation Guide - Verify your ISO image (Linux Mint, 2026); html; level `references`; training_use `private-only`.
- `kernel-kvm-api` - The Definitive KVM API Documentation (Linux kernel developers, 2026); html; level `references`; training_use `allowed`.
- `qemu-security` - QEMU System Emulation - Security (QEMU Project, 2026); html; level `references`; training_use `allowed`.
- `qemu-security-process` - QEMU Security Process (QEMU Project, 2026); html; level `references`; training_use `private-only`.
- `kernel-kconfig-language` - Kconfig Language (Linux kernel developers, 2026); html; level `references`; training_use `allowed`.
- `kspp-recommended-settings` - KSPP Recommended Settings (Linux Kernel Self-Protection Project, 2026); html; level `references`; training_use `private-only`.
- `kernel-self-protection` - Kernel Self-Protection (Cook, Kees; Linux kernel developers, 2026); html; level `references`; training_use `allowed`.
- `kernel-x86-iommu` - x86 IOMMU Support (Linux kernel developers, 2026); html; level `references`; training_use `allowed`.
- `kernel-vfio` - VFIO - Virtual Function I/O (Linux kernel developers, 2026); html; level `references`; training_use `allowed`.
- `xen-security-policy` - Xen Project Security Policy (Xen Project, 2026); html; level `references`; training_use `private-only`.
- `xen-xsa-148` - XSA-148: x86 PV guest privilege escalation via uncontrolled creation of large page mappings (Xen Project Security Team, 2015); html; level `references`; training_use `private-only`.
- `xen-xsa-182` - XSA-182: x86 privilege escalation in PV guests (pagetable fast-path) (Xen Project Security Team, 2016); html; level `references`; training_use `private-only`.
- `ubuntu-cve-2015-3456-venom` - CVE-2015-3456 (VENOM, QEMU FDC) - Ubuntu (Canonical, 2015); html; level `references`; training_use `private-only`.
- `ubuntu-cve-2016-5195-dirty-cow` - CVE-2016-5195 (Dirty COW) - Ubuntu (Canonical, 2016); html; level `references`; training_use `private-only`.
- `ubuntu-cve-2022-0847-dirty-pipe` - CVE-2022-0847 (Dirty Pipe) - Ubuntu (Canonical, 2022); html; level `references`; training_use `private-only`.
- `ubuntu-cve-2024-6387-regresshion` - CVE-2024-6387 (regreSSHion, OpenSSH) - Ubuntu (Canonical, 2024); html; level `references`; training_use `private-only`.
- `cisa-xz-utils-alert` - Reported Supply Chain Compromise Affecting XZ Utils, CVE-2024-3094 (CISA, 2024); html; level `references`; training_use `allowed`.
- `thunderclap-ndss2019` - Thunderclap: Exploring Vulnerabilities in Operating System IOMMU Protection via DMA from Untrustworthy Peripherals (Markettos, A. Theodore; Rothwell, Colin; Gutstein, Brett F.; Pearce, Allison; Neumann, Peter G.; Moore, Simon W.; Watson, Robert N. M., 2019); pdf; level `references`; training_use `private-only`.
- `cisa-aa21-321a-iran` - AA21-321A Iranian Government-Sponsored APT Cyber Actors Exploiting Microsoft Exchange and Fortinet Vulnerabilities (CISA; FBI; ACSC; NCSC-UK, 2021); html; level `references`; training_use `allowed`.
- `cisa-aa23-335a-irgc` - AA23-335A IRGC-Affiliated Cyber Actors Exploit PLCs (incl. US Water) (CISA; FBI; NSA; EPA; INCD, 2023); html; level `references`; training_use `allowed`.
- `cisa-aa24-241a-iran` - AA24-241A Iran-based Cyber Actors Enabling Ransomware Attacks on US Organizations (FBI; CISA; DC3, 2024); html; level `references`; training_use `allowed`.
- `cisa-aa24-038a-volt-typhoon` - AA24-038A PRC State-Sponsored Actors (Volt Typhoon) Compromise US Critical Infrastructure (CISA; NSA; FBI; Five Eyes partners, 2024); html; level `references`; training_use `allowed`.
- `thesis-litty-toronto` - Architectural Introspection and Applications (Litty, Lionel, 2010); pdf; level `phd`; training_use `private-only`.
- `thesis-unimi-hw-virt` - Hardware-Assisted Virtualization and its Applications to Systems Security (Fattori, Aristide, 2014); pdf; level `phd`; training_use `private-only`.
- `thesis-cam-pcie-tr934` - Exploitation from malicious PCI Express peripherals (UCAM-CL-TR-934) (Rothwell, Colin L., 2019); pdf; level `phd`; training_use `private-only`.
- `thesis-kemerlis-columbia` - Protecting Commodity Operating Systems through Strong Kernel Isolation (Kemerlis, Vasileios P., 2015); pdf; level `phd`; training_use `private-only`.
- `thesis-mehrab-vt` - On Improving the Security of Virtualized Systems through Unikernelized Driver Domain and VMM Compartmentalization and Specialization (Mehrab, A K M Fazla, 2023); pdf; level `phd`; training_use `private-only`.

## Linux kernel expert sources, second batch (2026-10-10)

Same rules as the first batch; `txt` is a third stored format. Qubes QSBs come only from the
reviewed path prefix `https://raw.githubusercontent.com/QubesOS/qubes-secpack/`.

- `intel-vtd-spec` - Intel Virtualization Technology for Directed I/O Architecture Specification, Rev 5.0 (D51397-017) (Intel Corporation, 2024); pdf; level `references`; training_use `private-only`.
- `amd-iommu-spec` - AMD I/O Virtualization Technology (IOMMU) Specification, 48882-PUB Rev 3.11 (Advanced Micro Devices, 2026); pdf; level `references`; training_use `private-only`.
- `csi-linux-updating` - Updating the CSI Linux Platform (incl. securing APT repositories) (CSI Linux, 2024); pdf; level `references`; training_use `private-only`.
- `qubes-qsb-001` - Qubes Security Bulletin #1: GUI daemon bug, Intel VT-d escape on non-IR hardware (Qubes OS Security Team, 2011); txt; level `references`; training_use `private-only`.
- `qubes-qsb-022` - Qubes Security Bulletin #22: Critical Xen bug in PV memory virtualization code (XSA-148) (Qubes OS Security Team, 2015); txt; level `references`; training_use `private-only`.
- `qubes-qsb-024` - Qubes Security Bulletin #24: Critical Xen bug in PV memory virtualization code (XSA-182) (Qubes OS Security Team, 2016); txt; level `references`; training_use `private-only`.
- `qubes-qsb-058` - Qubes Security Bulletin 058: Insufficient cache write-back under VT-d (XSA-321) (Qubes OS Security Team, 2020); txt; level `references`; training_use `private-only`.
- `qubes-qsb-079` - Qubes Security Bulletin 079: Two IOMMU-related Xen issues (XSA-399, XSA-400) (Qubes OS Security Team, 2022); txt; level `references`; training_use `private-only`.
- `qubes-qsb-095` - Qubes Security Bulletin 095: Missing IOMMU TLB flushing on x86 AMD systems (Qubes OS Security Team, 2023); txt; level `references`; training_use `private-only`.
- `qubes-qsb-100` - Qubes Security Bulletin 100: Incorrect handling of PCI devices with phantom functions (XSA-449) (Qubes OS Security Team, 2024); txt; level `references`; training_use `private-only`.
- `qubes-device-handling-security` - Qubes OS: Device handling security (Qubes OS Project, 2026); html; level `references`; training_use `allowed`.
- `qubes-architecture` - Qubes OS: Architecture (Qubes OS Project, 2026); html; level `references`; training_use `allowed`.
- `qubes-gui-security` - Qubes OS: GUI virtualization (Qubes OS Project, 2026); html; level `references`; training_use `allowed`.
- `kernel-apparmor` - AppArmor (Linux kernel admin guide, LSM) (Linux kernel developers, 2026); html; level `references`; training_use `allowed`.
- `kernel-lsm-index` - Linux Security Module Usage (Linux kernel developers, 2026); html; level `references`; training_use `allowed`.
- `ubuntu-apparmor` - AppArmor - Ubuntu Server documentation (Canonical, 2026); html; level `references`; training_use `private-only`.
- `ubuntu-usg` - Ubuntu Security Guide (USG) - CIS/DISA-STIG hardening (Canonical, 2026); html; level `references`; training_use `private-only`.
- `ubuntu-kernel-docs` - Ubuntu Kernel documentation (index) (Canonical, 2026); html; level `references`; training_use `private-only`.
- `ubuntu-security-team-faq` - Ubuntu security updates (Canonical, 2026); html; level `references`; training_use `private-only`.
- `arch-security-tracker` - Arch Linux security tracker - vulnerable issues (Arch Linux Security Team, 2026); html; level `references`; training_use `private-only`.
- `arch-security-team-wiki` - Arch Security Team - ArchWiki (Arch Linux, 2026); html; level `references`; training_use `allowed`.
- `arch-wiki-kernel-parameters` - Kernel parameters - ArchWiki (Arch Linux, 2026); html; level `references`; training_use `allowed`.
- `arch-wiki-apparmor` - AppArmor - ArchWiki (Arch Linux, 2026); html; level `references`; training_use `allowed`.
- `kali-recompiling-kernel` - Recompiling the Kali Linux Kernel (OffSec / Kali Linux, 2026); html; level `references`; training_use `private-only`.
- `kali-root-policy` - Kali Linux Root User Policy (OffSec / Kali Linux, 2026); html; level `references`; training_use `private-only`.
- `mint-2016-iso-hack` - Beware of hacked ISOs if you downloaded Linux Mint on February 20th! (official project statement) (Lefebvre, Clement; Linux Mint, 2016); html; level `references`; training_use `private-only`.
- `thesis-kuleuven-vanbulck` - Microarchitectural Side-Channel Attacks for Privileged Software Adversaries (Van Bulck, Jo, 2020); pdf; level `phd`; training_use `private-only`.
- `thesis-luebeck-wilke` - Security Analysis of Confidential VMs on Modern Server Architectures (Wilke, Luca, 2024); pdf; level `phd`; training_use `private-only`.
- `thesis-umd-petroni` - Property-Based Integrity Monitoring of Operating System Kernels (Petroni, Nick Louis, Jr., 2008); pdf; level `phd`; training_use `private-only`.
- `thesis-tugraz-lipp` - Exploiting Microarchitectural Optimizations from Software (Lipp, Moritz, 2021); pdf; level `phd`; training_use `private-only`.

## Peer-reviewed postdoctoral papers (2026-10-10)

- `pd-cry-01` (cryptographer) - Towards Low-Energy Leakage-Resistant Authenticated Encryption from the Duplex Sponge Construction (Guo, Chun Fen; Pereira, Olivier; Peters, Thomas; Standaert, François-Xavier, 2020; IACR Transactions on Symmetric Cryptology); training_use `allowed`.
- `pd-cry-02` (cryptographer) - TEDT, a Leakage-Resist AEAD Mode for High Physical Security Applications (Berti, Francesco; Guo, Chun Fen; Pereira, Olivier; Peters, Thomas; Standaert, François-Xavier, 2019; IACR Transactions on Cryptographic Hardware and Embedded Systems); training_use `allowed`.
- `pd-cry-03` (cryptographer) - Integral Cryptanalysis Using Algebraic Transition Matrices (Beyne, Tim; Verbauwhede, Michiel, 2023; IACR Transactions on Symmetric Cryptology); training_use `allowed`.
- `pd-cry-04` (cryptographer) - Defeating Low-Cost Countermeasures against Side-Channel Attacks in Lattice-based Encryption (Ravi, Prasanna; Paiva, Thales Bandiera; Jap, Dirmanto; D’Anvers, Jan-Pieter; Bhasin, Shivam, 2024; IACR Transactions on Cryptographic Hardware and Embedded Systems); training_use `allowed`.
- `pd-cry-05` (cryptographer) - Sound Hashing Modes of Arbitrary Functions, Permutations, and Block Ciphers (Daemen, Joan; Mennink, Bart; Assche, Gilles Van, 2018; IACR Transactions on Symmetric Cryptology); training_use `allowed`.
- `pd-cry-06` (cryptographer) - Searching for Subspace Trails and Truncated Differentials (Leander, Gregor; Tezcan, Cihangir; Wiemer, Friedrich, 2018; IACR Transactions on Symmetric Cryptology); training_use `allowed`.
- `pd-qmp-01` (quantum-mechanics-professor) - Experimental investigation of high-dimensional quantum key distribution protocols with twisted photons (Bouchard, Frédéric; Heshami, Khabat; England, Duncan G.; Fickler, Robert; Boyd, Robert W.; Englert, Berthold-Georg; Sánchez-Soto, Luis Lorenzo; Karimi, Ebrahim, 2018; Quantum); training_use `allowed`.
- `pd-qmp-03` (quantum-mechanics-professor) - Witnessing quantum memory in non-Markovian processes (Giarmatzi, Christina; Costa, Fabio, 2021; Quantum); training_use `allowed`.
- `pd-qmp-04` (quantum-mechanics-professor) - Operational applications of the diamond norm and related measures in quantifying the non-physicality of quantum maps (Regula, Bartosz; Takagi, Ryuji; Gu, Mile, 2021; Quantum); training_use `allowed`.
- `pd-mat-01` (mathematician) - A CONTACT INVARIANT IN SUTURED MONOPOLE HOMOLOGY (Baldwin, John A.; Sivek, Steven, 2016; Forum of Mathematics Sigma); training_use `allowed`.
- `pd-psy-03` (psychologist) - Is loss-aversion magnitude-dependent? Measuring prospective affective judgments regarding gains and losses (Mukherjee, Sumitava; Sahay, Arvind; Pammi, V. S. Chandrasekhar; Srinivasan, Narayanan, 2017; Judgment and Decision Making); training_use `allowed`.
- `pd-psy-04` (psychologist) - Non-monetary reinforcement effects on pro-environmental behavior (Lange, Florian; Dewitte, Siegfried, 2023; Journal of Economic Psychology); training_use `private-only`.
- `pd-sys-01` (system-administrator) - The Ivory Tower Syndrome: Operators' Reflections on Academic BGP Security Solutions (Inamdar, Aleeza Suhel; Fiebig, Tobias; Kaur, Mannat, 2026; 35th USENIX Security Symposium (USENIX Security 26)); training_use `private-only`.
- `pd-ker-01` (linux-kernel-expert) - HyperPill: Fuzzing for Hypervisor-bugs by Leveraging the Hardware Virtualization Interface (Bulekov, Alexander; Liu, Qiang; Egele, Manuel; Payer, Mathias, 2024; 33rd USENIX Security Symposium (USENIX Security 24)); training_use `private-only`.
- `pd-ker-02` (linux-kernel-expert) - GlobalConfusion: TrustZone Trusted Application 0-Days by Design (Busch, Marcel; Mao, Philipp; Payer, Mathias, 2024; 33rd USENIX Security Symposium (USENIX Security 24)); training_use `private-only`.

## Early-career peer-reviewed papers (2026-10-10)

- `ec-sta-01` (statistician) - High-dimensional Ising model selection with Bayesian information criteria (Barber, Rina Foygel; Drton, Mathias, 2015; Electronic Journal of Statistics); training_use `allowed`.
- `ec-sta-02` (statistician) - Probabilistic Fréchet means for time varying persistence diagrams (Munch, Elizabeth; Turner, Katharine; Bendich, Paul; Mukherjee, Sayan; Mattingly, Jonathan Christopher; Harer, John, 2015; Electronic Journal of Statistics); training_use `allowed`.
- `ec-sta-03` (statistician) - Distribution theory for hierarchical processes (Camerlenghi, Federico; Lijoi, Antonio; Orbanz, Peter; Pruenster, Igor, 2018; The Annals of Statistics); training_use `private-only`.
- `ec-sta-04` (statistician) - Augmented minimax linear estimation (Hirshberg, David A.; Wager, Stefan, 2021; The Annals of Statistics); training_use `private-only`.
- `ec-sta-05` (statistician) - Mitigating Bias in Generalized Linear Mixed Models: The Case for Bayesian Nonparametrics (Antonelli, Joseph; Trippa, Lorenzo; Haneuse, Sebastien, 2016; Statistical Science); training_use `private-only`.
- `ec-ker-01` (linux-kernel-expert) - Statically Discover Cross-Entry Use-After-Free Vulnerabilities in the Linux Kernel (Zhang, Hang; Kim, Jangha; Yuan, Chuhong; Qian, Zhiyun; Kim, Taesoo, 2025; NDSS Symposium 2025); training_use `private-only`.
- `ec-sys-01` (system-administrator) - "I Have No Idea What I'm Doing" - On the Usability of Deploying HTTPS (Krombholz, Katharina; Mayer, Wilfried; Schmiedecker, Martin; Weippl, Edgar, 2017; 26th USENIX Security Symposium); training_use `private-only`.
- `ec-sys-02` (system-administrator) - "I needed to solve their overwhelmness": How System Administration Work was Affected by COVID-19 (Kaur, Mannat; Parkin, Simon; Janssen, Marijn; Fiebig, Tobias, 2022; Proc. ACM Hum.-Comput. Interact. 6 (CSCW2), Article 390); training_use `allowed`.
- `ec-psy-01` (psychologist) - An Observational Investigation of Reverse Engineers' Processes (Votipka, Daniel; Rabin, Seth; Micinski, Kristopher; Foster, Jeffrey S.; Mazurek, Michelle L., 2020; 29th USENIX Security Symposium); training_use `private-only`.
- `ec-psy-02` (psychologist) - Being Hacked: Understanding Victims' Experiences of IoT Hacking (Rostami, Asreen; Vigren, Minna; Raza, Shahid; Brown, Barry, 2022; Eighteenth Symposium on Usable Privacy and Security (SOUPS 2022)); training_use `private-only`.
- `ec-lrp-01` (it-larp-coach) - Understanding security mistakes developers make: Qualitative analysis from Build It, Break It, Fix It (Votipka, Daniel; Fulton, Kelsey R.; Parker, James; Hou, Matthew; Mazurek, Michelle L.; Hicks, Michael, 2020; 29th USENIX Security Symposium); training_use `private-only`.

## Early-career papers, second set (2026-10-10)

- `ec4-psy-01` (psychologist) - Gaze patterns disclose the link between cognitive reflection and sophistication in strategic interaction (Zonca, Joshua; Coricelli, Giorgio; Polonio, Luca, 2020; Judgment and Decision Making); training_use `allowed`.
- `ec4-psy-02` (psychologist) - Norm shifts under the strategy method (Columbus, Simon; BOHM, ROBERT M., 2021; Judgment and Decision Making); training_use `allowed`.
- `ec4-psy-03` (psychologist) - Prevention is better than cure! Designing information security awareness programs to overcome users' non-compliance with information security policies in banks (Bauer, Stefan; Bernroider, Edward W. N.; Chudzikowski, Katharina, 2017; Computers & Security 68:145-159); training_use `allowed`.
- `ec4-mat-01` (mathematician) - Pure PSVD approach to Sylvester-type quaternion matrix equations (He, Zhuo-Heng, 2019; Electronic Journal of Linear Algebra 35:266-284); training_use `private-only`.
- `ec4-mat-02` (mathematician) - On the inverse of a class of bipartite graphs with unique perfect matchings (Panda, Swarup Kumar; Pati, Sukanta, 2015; Electronic Journal of Linear Algebra 29:89-101); training_use `private-only`.
- `ec4-mat-03` (mathematician) - On the distance and distance signless Laplacian eigenvalues of graphs and the smallest Geršgorin disc (Atik, Fouzul, 2018; Electronic Journal of Linear Algebra 34:191-204); training_use `private-only`.
- `ec4-mat-04` (mathematician) - On the closure of the completely positive semidefinite cone and linear approximations to quantum colorings (Burgdorf, Sabine; Laurent, Monique; Piovesan, Teresa, 2017; Electronic Journal of Linear Algebra); training_use `private-only`.

## Pending 2025-2026 research candidates

[Persona research refresh](RESEARCH_2025_2026.md) records primary-source candidates, benefits, correction/supersession evidence and admission requirements. It is not part of the approved index. Source originals, rights review, author metadata and staged deployment remain pending; the live library and current writer queue were not changed.

# Local Stegdetect detection and gap tracking

The [Chicone review](CHICONE_SCREENING_REVIEW.md) documents an owner-adjudicated
mathematics false-positive incident. Its selected held subset and mixed gate reasons
are kept separate from the public synthetic evaluation and its rate denominators.

Run from any PowerShell folder:

```powershell
python "E:\speedzone_MS\LARPUS\scripts\evaluate-stegdetect.py"
```

The owner-side command scans the public authored corpus locally. It does not call a model, load the GPU, use the internet, change detector policy or restart production. Reports are ignored under `data/evals/stegdetect/`: timestamped-by-run-ID JSON receipts, `latest.json`, `latest.md` and append-only `history.jsonl`. Each receipt includes dataset, scanner Python sources and gate fingerprints. Keep receipts when comparing versions. No raw sample text is copied to reports; case IDs/families are bounded identifiers. A private corpus can be supplied with `--corpus "E:\path\private-corpus.json"`; its labels still need review and it must remain outside Git.

## Two different measurements

- **stegdetect:** complete scanner decisions to hold/review/block or change the forwarding candidate count positive against the `carrier` label.
- **larpus_gate:** the combined Unicode, control/format and injection rules count positive against the `hold` label.

A `carrier` label is an authored target for suspicious carrier-like text, not proof of a hidden payload or intent. Controls and excessive combining marks are included as aspirational coverage probes; the separate LARPUS rules can catch cases outside the installed scanner's narrower scope. Do not interpret their misses as violations of an upstream promised capability. `hold` describes the desired input policy: the quoted security discussion is labeled benign, making an overly broad rule visible as a false positive. Label changes alter the question being measured; review them separately from detector changes.

No detection credit is earned from errors or incomplete scans, including input-limit exhaustion. These are reported inconclusive even though the production gate fails closed. Incomplete gate scans carry completeness metadata internally; existing HTTP behavior is unchanged. Complete held scans remain conclusive. Neither classification nor a held request proves that the model would have followed an attack.

## Rates and denominators

Detection rate = TP/(TP+FN); false-negative rate = FN/(TP+FN); false-positive rate = FP/(FP+TN); precision = TP/(TP+FP). Zero denominators are `null`/unknown. Conclusive positive/negative denominators, total cases and inconclusive counts are explicit. Do not compare aggregate rates across different dataset hashes or changed class mix as if only the detector changed. Inspect family-level results first; history is evidence to analyze, not a regression threshold or a production security score.

The initial corrected 21-case synthetic run recorded:

| Layer | TP | FP | TN | FN | Inconclusive | Detection | FPR | FNR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stegdetect | 2 | 0 | 15 | 3 | 1 | 40% (2/5) | 0% (0/15) | 60% (3/5) |
| LARPUS gate | 8 | 1 | 9 | 2 | 1 | 80% (8/10) | 10% (1/10) | 20% (2/10) |

These tiny authored samples do not estimate real-world rates. Zero observed
scanner false positives is not proof of zero false positives. The gate misses
the paraphrased and encoded override probes and holds the benign quotation.
Scanner misses include a single zero-width space, a NUL control and the
combining-run probe; LARPUS's additional rules hold those. The over-limit
sample is inconclusive, not a detected attack. Exact case IDs and per-family
denominators are recorded in JSON.

## Active-image gate recheck and expanded challenge (2026-10-22)

The downstream FP/FN comparison depends on the boundary:
`runtime/text_filter.py` is the **combined LARPUS input gate after Stegdetect**;
`runtime/inference_broker.py` is a later structural inference broker. The broker
checks the route, framing, approved system-template hash, lane, model options and
resource limits. It does **not** classify the meaning of user text, so the
Unicode/attack FP/FN labels below apply to the gate, not to the broker.

The active release was `346773e17fd54b7784fd3148b07a4b0e`. The checkout,
frozen release and running agent copies of `runtime/text_filter.py` agreed at
SHA-256 `0caec5f19ef7be48e5794d6032a5ddf9e6fbe324e402090ff8182a36b5beffaa`.
The running broker's source matched the frozen release at SHA-256
`530a21cb074180e5411c37b68055c1bdcef07fa782cdecce048478e37996b8a1`.
The running agent contained Stegdetect 0.2.0 with package-file digest
`5668ca812e9d90ff18744b76cd702c1b6a6d6b50d8735343867fba3902900308`.
That differs from the Windows-installed 0.2.0 digest used in the Stegdetect
project's initial baseline (`a4964371b35ce04906768712904be96c484646fb0a53f042e13a93ab2f8aac0b`).
Therefore the active-image results below were recomputed inside the running
agent container; the host-package result was not substituted for them.

The 21-case authored corpus was streamed to `gate.inspect_message()` inside
the active agent without model calls or release changes. Its gate matrix was
TP 8, FP 1, TN 9, FN 2, inconclusive 1: **FPR 1/10 (10%) and FNR 2/10
(20%)** on that corpus. `paraphrase` and `encoded` were allowed; `quoted`
was held for `instruction_override`; `long` was inconclusive from an incomplete
scan. This recheck agrees with the prior small-set counts. It is neither a
production rate nor proof of attack success.

The separate 20× synthetic cohort came from the Stegdetect project's
`scripts/expanded_fpfn.py` at local commit `64db4d0`, corpus SHA-256
`42a7c26f7e17b9c56789f8de330127cb7ad9bfc51cd0c9fbb45a5d268dde1a0d`.
It contains 320 benign variants of 32 project-selected seeds and 16,000 carrier
challenges in eight families. The same strings were streamed into the active
agent's gate; no raw strings were written to the report. The result was:

| Cohort | Active LARPUS gate result | Interpretation |
|---|---:|---|
| Benign variants held | 30/320 (9.375%) | 20 `hidden_format`, 10 Unicode-policy holds; 3 of 32 seed situations affected |
| Project-designated intervention challenges allowed | 2,000/12,000 (16.7%) | All from the known low-density mixed-script family |
| Other intervention challenges held | 10,000/12,000 | Five carrier families, 2,000 each |
| Ambiguous invisible-format markers held | 572/2,000 | Not counted as attack catches or misses |
| Ambiguous unusual-space markers held | 0/2,000 | Not counted as attack catches or misses |
| Incomplete/error cases | 0/16,320 | All decisions conclusive in this bounded run |

The extra benign holds relative to Stegdetect alone are family emoji and soft
hyphen variants rejected by the LARPUS `hidden_format` rule; England-flag
variants are held by the Unicode policy. Each affected seed has ten correlated
variants. The 2,000 allowed challenge strings are only **40 Unicode structures**
repeated with numeric IDs. They carry no malicious instructions, and the
LARPUS regex rules do not inspect the 50%-density homoglyph structure. Thus
16.7% is a **synthetic carrier false-allow share**, not an estimated
prompt-injection false-negative rate. Changing the corpus or labels changes
the denominator and cannot be treated as a detector improvement/regression.

The checkout broker's four focused `test_inference_broker.py` tests passed,
including valid-request acceptance, rejected controls, duplicate/nonfinite
fields and fake-upstream framing. This is structural evidence only. No live
chat request, model inference, broker throughput test, production shadow
sample, or independent label review was performed. The LARPUS training run and
all services were left running. The active-image check used CPU-only
`podman exec` with synthetic text; it did not activate, stop, or modify a
release. A future broker validity estimate needs a separately labeled set of
valid and invalid **request shapes/capabilities**, not these semantic carrier
labels. A real input-gate field rate needs consented source-separated traffic
and independent review of allows as well as holds.

## Stated coverage and gaps

`evals/stegdetect.json` declares twenty families. Fifteen have at least one example; this is sample presence, not exhaustive coverage. Variation selectors, homoglyphs, acrostics, image/audio carriers and representative real-world multilingual traffic are explicitly untested. A family with only benign samples cannot establish its detection rate; a positive-only family cannot establish FPR. Script/script-language labels do not substitute for native-speaker review. No natural traffic is collected automatically.

The corpus is authored synthetic and not independently human-labeled. Independent review of the tracker found corrupted Unicode fixtures and second-scan incompleteness accounting; both were corrected with regression tests. Tooling review is not independent validation of ground-truth labels. Larger, consented, source-separated benign/positive corpora and independent human review are needed before making deployment FP/FN claims. Keep any tuning set separate from a frozen evaluation set.

## Maintenance

Run the command before and after a detector/gate change and retain the receipts. Investigate mismatch IDs by reading the authorized source corpus locally; do not publish private samples or prompts. The report intentionally exposes misses rather than forcing every metric green. Missing/invalid/duplicate labels fail the command; no successful receipt is created for malformed corpus input. Full scanner failures become inconclusive rows. This tracker is manual and local: scheduled evaluation and production sampling are not implemented.

The tracker was subsequently included in the active snapshot recorded in [STATUS.md](STATUS.md). New changes still require the ordinary release flow. Activation did not change the upstream detector dependency or turn synthetic measurements into production-rate evidence.

## Validation evidence

The isolated suite reported 218 tests OK with two skips. After metadata hardening, all eight focused evaluation tests passed and the complexity gate passed unchanged. An independent read-only tooling review verified corrected Unicode fixtures and incomplete-scan accounting; ground-truth labels remain unreviewed by independent humans. Early receipts generated before Unicode correction are invalid for comparison; retain them as development history, not baseline evidence. Match the corrected corpus fingerprint before using rates.

# Local Stegdetect detection and gap tracking

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

These tiny authored samples do not estimate real-world rates. Zero observed scanner false positives is not proof of zero false positives. The gate misses the paraphrased and encoded override probes and holds the benign quotation. Scanner misses include a single zero-width space, a NUL control and the combining-run probe; LARPUS's additional rules hold those. The over-limit sample is inconclusive, not a detected attack. Exact case IDs and per-family denominators are recorded in JSON.

## Stated coverage and gaps

`evals/stegdetect.json` declares twenty families. Fifteen have at least one example; this is sample presence, not exhaustive coverage. Variation selectors, homoglyphs, acrostics, image/audio carriers and representative real-world multilingual traffic are explicitly untested. A family with only benign samples cannot establish its detection rate; a positive-only family cannot establish FPR. Script/script-language labels do not substitute for native-speaker review. No natural traffic is collected automatically.

The corpus is authored synthetic and not independently human-labeled. Independent review of the tracker found corrupted Unicode fixtures and second-scan incompleteness accounting; both were corrected with regression tests. Tooling review is not independent validation of ground-truth labels. Larger, consented, source-separated benign/positive corpora and independent human review are needed before making deployment FP/FN claims. Keep any tuning set separate from a frozen evaluation set.

## Maintenance

Run the command before and after a detector/gate change and retain the receipts. Investigate mismatch IDs by reading the authorized source corpus locally; do not publish private samples or prompts. The report intentionally exposes misses rather than forcing every metric green. Missing/invalid/duplicate labels fail the command; no successful receipt is created for malformed corpus input. Full scanner failures become inconclusive rows. This tracker is manual and local: scheduled evaluation and production sampling are not implemented.

All changes remain checkout-only until staged, prepared and activated through the ordinary release flow. No upstream dependency, model or active release was changed.

## Validation evidence

The isolated suite reported 218 tests OK with two skips. After metadata hardening, all eight focused evaluation tests passed and the complexity gate passed unchanged. An independent read-only tooling review verified corrected Unicode fixtures and incomplete-scan accounting; ground-truth labels remain unreviewed by independent humans. Early receipts generated before Unicode correction are invalid for comparison; retain them as development history, not baseline evidence. Match the corrected corpus fingerprint before using rates.

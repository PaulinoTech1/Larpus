# Output DLP synthetic error-rate baseline — 2026-10-22

For the cross-filter comparison, including Stegdetect false-positive and
false-negative mechanisms, see [the text-filter error report](FILTER_FP_FN_2026-10-22.md).

Measured at approximately 6:04 PM Eastern. This was a CPU-only evaluation of
`runtime.dlp.inspect_output` and a two-case `gate` smoke check. It made no model,
gateway, broker, network, or training request. No active service was restarted.
The checkout `runtime/dlp.py` and `config/dlp.json` SHA-256 hashes matched the
active `larpus-agent-346773e17fd54b7784fd3148b07a4b0e` image byte for byte.
Four read-only probes in that image reproduced clean, credential, fictional
private-address, and split-address scanner behavior.

## Contract and labels

The target behavior is to withhold an answer containing an actual protected
value, credential-like token, private address, local path, copied prompt line,
or hidden control, while releasing a useful answer that contains no sensitive
disclosure. **Assumption:** a clearly fictional network example, a dummy token
in a tutorial, and a generic path example are safe to release. If the owner's
policy is instead to hold these categories regardless of context, the 30
reported false positives are intentional policy holds. The corpus contains
only synthetic values and no known real secret. The labels are therefore a
judgment of intended answer behavior, not a check against live disclosures.

Run `python -m scripts.eval_output_dlp` from the repo root to reproduce the
deterministic, hand-labeled cases. The corpus has 73 should-hold cases across
credential assignments/tokens, addresses, paths, configured private values,
copied prompt text, and controls; and 60 should-release cases across coaching,
general technical content, fictional private-network examples, dummy credential
examples, generic paths, and ordinary formatting. Families are deliberately
weighted toward known boundary conditions. Cases within a family share syntax;
they are not independent samples from actual LARPUS traffic.

| Labeled class | Held | Released | Error rate on this class |
|---|---:|---:|---:|
| Should hold | 73 | 0 | False negatives: **0/73 (0%)** |
| Should release | 30 | 30 | False positives: **30/60 (50%)** |

All 30 false positives were the 10 fictional private-network, 10 dummy-credential,
and 10 generic-path examples. Plain coaching, general technical explanation,
and ordinary formatting were 30/30 released. The 50% figure is a property of
this intentionally difficult mix and must not be presented as the production
false-positive rate. With only 73 synthetically chosen positive cases, 0 misses
does not establish a low real-world false-negative rate.

Six exploratory challenges were excluded from those rates. Five disclosure-like
cases escaped the scanner: a spaced private address, split `password` keyword,
HTML-entity-encoded address, base64 encoding of a value absent from the policy,
and a paraphrased prompt line. These are concrete blind spots, although arbitrary
encoding, unknown secrets, and semantic paraphrases are already outside the
documented deterministic contract. One invalid-octet address (`192.168.999.999`)
was held by the private-address regex; it is an additional example of
overmatching, excluded from the primary labeled corpus.

The temporary-quarantine gate smoke check returned 200 with identical content
for a clean example, and 422 with no `content` field and one held record for a
synthetic credential. `python -m unittest tests.test_dlp tests.test_streaming`
passed 13 tests. The streaming tests include fragmented credentials, addresses,
paths, and protected strings; they do not estimate live stream error rates.
`python scripts/complexity.py check` failed on existing findings in
`runtime/knowledge.py`, `runtime/rag_eval.py`, and `scripts/mtrageval_local.py`;
it reported no finding in the new evaluator after its corpus builder was split.

**Assessment:** High confidence in these exact counts and active-image scanner
parity; low confidence that these rates predict deployed traffic. A real-world
estimate requires a consented, privacy-preserving sample of actual generated
outputs, human labels independent of detector results, and separate accounting
for held and released replies. No such sample was collected. The principal
design tradeoff is that relaxing syntax rules could reduce tutorial holds while
increasing disclosure risk. Keep the current fail-closed gate until any change
has a labeled, representative comparison and negative security tests.

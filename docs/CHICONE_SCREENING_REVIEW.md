# Chicone mathematical-text false-positive review

Recorded October 14, 2026. Source: Carmen Chicone, *Ordinary Differential
Equations with Applications*. The owner supplied the PDF and reviewed the local
held-passage report before explicitly approving all 52 passages for reference use.

## Observed result and adjudication

The existing extraction/segmentation produced 1,621 passages. The combined LARPUS
gate held 52 passages across 47 PDF pages:

| Hold reason | Passages | Interpretation retained |
| --- | ---: | --- |
| `hidden_control` | 19 | Control characters in extracted reference text triggered the LARPUS gate. |
| `unicode_carrier_or_incomplete_scan` | 33 | Combined reason includes Unicode findings, candidate transformation or incomplete scanning; the original receipt does not establish which occurred in each case. |

The owner judged all 52 reviewed passages benign mathematical reference material.
Record these as **owner-adjudicated false-positive holds**, not independently proven
absence of concealed content. They are not 52 confirmed Stegdetect classification
false positives: 19 originate in the additional LARPUS control rule, and incomplete
scans must remain inconclusive under the evaluation methodology.

The PDF extraction also reported missing optional font-decoding support. Mathematical
notation/font encodings are a plausible source of findings, but exact causal
attribution has not been established. Approval does not certify that equations
were extracted correctly. The original PDF, extracted review text, code-point
inventory and scanner findings remain owner-local and unchanged.

## Scope and limitations

Only the held subset received this explicit owner adjudication. Do not derive a
corpus-wide false-positive rate, precision, false-negative rate or detector-quality
claim from that selected sample. False negatives and unheld passage correctness
were not assessed. The screening report lacks per-case upstream completeness and
finding details needed to separate all 33 mixed-reason cases retrospectively.
Future reviews should retain those details alongside gate reason and reviewer label.

## Action after review

Exact source/text checksums were pinned in the reference-review configuration.
The narrow reference path allows these reviewed Unicode/control holds while still
checking instruction-override and role-spoof patterns. Scanner unavailability is
not overridden. User input and generated replies keep ordinary filtering; other
math/quantum documents do not inherit this approval. Changed text needs new review.

Admission added 1,621 passages to the checkout index and 282 distinct GPU windows.
Earlier index rows and completed note keys were retained. The active frozen release
was not changed. Human acceptance, acquisition rights, extraction fidelity and
deployment acceptance remain separate evidence questions.

Private receipts are under `data/research-inbox/chicone-ordinary-differential-equations/`:
`screening.json`, `held-review.json`, `held-review.html`, `manifest.json` and
`false-positive-review.json`. No original or passage text is reproduced here.

# Mathematical Unicode review patterns

On October 14, 2026 the owner approved all 106 held passages in Sandro Salsa's
*Partial Differential Equations in Action: From Modelling to Theory* (2008,
revised reprint 2009). A detailed reinspection showed that every scan completed;
all holds were mixed-script findings, not scanner failures. The owner judged the
Greek notation legitimate mathematical reference content.

| Symbol | Code point | Unicode name | Recorded findings |
| --- | --- | --- | ---: |
| α | U+03B1 | GREEK SMALL LETTER ALPHA | 94 |
| ε | U+03B5 | GREEK SMALL LETTER EPSILON | 86 |
| κ | U+03BA | GREEK SMALL LETTER KAPPA | 6 |
| ν | U+03BD | GREEK SMALL LETTER NU | 7 |
| ρ | U+03C1 | GREEK SMALL LETTER RHO | 212 |
| τ | U+03C4 | GREEK SMALL LETTER TAU | 108 |
| χ | U+03C7 | GREEK SMALL LETTER CHI | 14 |

These 527 finding occurrences belong to 106 passages, not 527 distinct failures
or documents. The mixed-script rule identifies visually confusable Greek/Latin
characters. Such notation can be legitimate in mathematics but suspicious in other
contexts. No transliteration or replacement was performed; changing rho to Latin p,
for example, could change mathematical meaning.

`config/mathematics-review-patterns.json` is an explanatory review-pattern ledger,
not an automatic symbol allowlist. Actual exceptions live in
`config/reference-reviews.json`, pinned to source identity and exact passage/window
hashes. Human review is required for newly held mathematics and quantum references.
Neither a role name nor the presence of these symbols grants approval to new text.
Input conversation, generated output, instruction-override/role-spoof patterns and
scanner unavailability keep their existing checks.

The original, reviewed passages and detailed findings remain private under the
source's research-inbox directory. `symbol-findings.json` retains per-case rule,
offset, code points, completeness and finding-truncation status. Public counts are
owner-adjudicated false-positive findings in this selected subset, not independent
verification of payload absence or a general detector false-positive rate.

Admission includes all 1,216 extracted passages. Extraction merged some word
spacing; equations and hypotheses should still be compared with original pages.
The checkout index and supplemental GPU queue include the source; production
retrieval requires staged preparation and activation. Earlier index rows and saved
notes remain intact. Acquisition permission is a separate question from screening.

# Text-filter false-positive and false-negative evidence — 2026-10-22

This report compares three distinct boundaries: the standalone Stegdetect
package, the combined LARPUS input gate that uses it, and LARPUS's output DLP.
The percentages below describe specific authored synthetic corpora. They are
**not measured production rates** and should not be added or averaged. A
separate owner review of held mathematics passages is described below.

| Boundary and labeled set | Benign outcomes | Challenge outcomes | Important qualification |
|---|---|---|---|
| Stegdetect 0.2.0, Balanced | 20/320 (6.25%) sent to review; 0 blocked | 2,000/12,000 (16.7%) intervention-designated carriers allowed | 32 benign seed situations, 10 variants each; the misses are 40 Unicode structures repeated with IDs |
| Stegdetect 0.2.0, Contextual | 10/320 (3.125%) sent to review; 0 blocked | 2,000/12,000 (16.7%) intervention-designated carriers allowed | Same corpus and same miss family |
| Active LARPUS combined input gate | 30/320 (9.375%) held | 2,000/12,000 (16.7%) intervention-designated carriers allowed | Its additional hidden-format rule accounts for extra benign holds |
| Active-code output DLP | 30/60 (50%) labeled benign replies held | 0/73 canonical should-hold replies released; five separate evasion probes escaped | Benign set deliberately concentrates examples that resemble protected syntax |

## Stegdetect false-positive detail

The standalone 20× Stegdetect evaluation used 32 project-chosen benign seeds in
ten text envelopes each. Under Balanced policy, all ten family-emoji variants
and all ten England-flag variants went to **manual review**: 20/320. Under
Contextual, only the ten England-flag variants went to manual review: 10/320.
None was blocked. Thus **100% of the observed standalone benign interruptions
were review decisions**, not blocks. These are two and one affected seed
situations respectively, not 20 and 10 independent natural-language errors.
The running LARPUS input gate held 30/320: those two groups plus ten soft-hyphen
variants. Its extra holds arise from its own `hidden_format` rule and must not
be attributed to the standalone package. The package in the Windows evaluation
and the one in the active agent were both version 0.2.0 but had different file
digests; the active input-gate numbers were independently checked in the agent.

An owner-adjudicated real-document incident offers a different kind of
evidence: the combined LARPUS gate held 52 of 1,621 Chicone mathematics
passages, and the owner judged all 52 held passages benign. Nineteen holds
had the LARPUS `hidden_control` reason; 33 had a combined Unicode/carrier or
incomplete-scan reason that cannot be decomposed retrospectively. These are
**52 owner-adjudicated gate holds**, not 52 proven standalone Stegdetect false
positives. The unheld passages were not adjudicated, so 52/1,621 is not a
validated false-positive rate. See [the incident review](CHICONE_SCREENING_REVIEW.md).

## Stegdetect false-negative detail

Of the 16,000 constructed carrier variants, six families (12,000 variants)
were designated as requiring intervention by the project authors. Five
families were all held. The sixth, **below-density mixed-script text**, was
allowed in all 2,000 variants under both policies; none reached manual review
or block. Each text contains a Latin prefix, `n` Cyrillic `а` characters
(`U+0430`, a Latin-`a` lookalike), `n` copies of a nonconfusable Cyrillic
diluter, and a numeric ID, with `n` from 1 to 8. Five diluters give 40
Unicode structures; the numeric ID repeats each structure 50 times. The
confusable share is 50%, below the scanner's 90% density threshold. The
installed-package audit found no finding category in any of these 2,000
cases, and `candidate_text` equaled the original. The combined LARPUS input
gate allowed the same 2,000 variants. They contain no attack instructions,
so this is a **synthetic carrier false-allow share**, not evidence of 2,000
successful prompt injections or a field security FNR.

The other 4,000 carrier variants contain isolated invisible-format or unusual
space markers. Their intent is ambiguous; they were excluded from the
12,000-case intervention denominator. The smaller 21-case LARPUS authored
evaluation gave standalone Stegdetect 3 misses among 5 labeled carriers
(60%); those included a single zero-width space, a NUL control, and a
combining run. LARPUS's additional input rules held those cases. That small
corpus uses an aspirational carrier label and must not be pooled with the
expanded challenge. The 20× corpus and miss-cohort structure come from the
Stegdetect project's `docs/EXPANDED_FP_FN_2026-10-22.md` and aggregate JSON
at local commit `64db4d0`, corpus SHA-256
`42a7c26f7e17b9c56789f8de330127cb7ad9bfc51cd0c9fbb45a5d268dde1a0d`.
The [LARPUS input-gate report](STEGDETECT_EVALUATION.md) records the active
agent recheck and the separate broker boundary.

## Output-DLP false-positive detail and missed challenges

The deterministic [output-DLP evaluation](OUTPUT-DLP-EVAL-2026-10-22.md)
contains 60 labeled benign replies. It released all 30 plain-coaching,
general-technical, and ordinary-formatting replies. It held all 30 replies
that gave fictional private-network examples, dummy credential examples, or
generic local-path examples (ten in each group). The label assumes a clearly
fictional tutorial example is safe to answer. If policy intentionally holds
all such syntax, these 30 are expected policy holds rather than errors. The
50% result is driven by this deliberately balanced edge-case mix.

The same evaluation held all 73 canonical protected examples. Outside that
denominator, five disclosure-like probes escaped: a spaced private address,
a split `password` keyword, an HTML-entity-encoded address, base64 of an
unknown secret, and a paraphrased system line. Arbitrary encoding, unknown
secrets, and semantic paraphrases exceed the documented deterministic DLP
contract. An invalid-octet address was held, illustrating regex overmatching.
A temporary-quarantine gate smoke check returned 200 for clean text and 422
without content for a synthetic credential. No real secrets were used.

## Interpretation and next measurement

Confidence is **high** in the reproduced synthetic counts and the identified
Unicode/syntax mechanisms; confidence is **low** in extrapolating any of these
fractions to production traffic. All expanded labels were project-authored,
correlated, and unreviewed by an independent labeler. The Chicone review
adjudicated only selected holds. The output-DLP corpus is also authored and
enriched for likely overmatches. Neither review sampled allows for hidden
leaks or measured model compliance with a malicious instruction.

A defensible operational estimate needs consented, source-separated output
and input samples; independent labels for a prespecified sample of **both**
holds and allows; explicit inconclusive counts; and separate rates by filter,
policy, and content family. Keep the present fail-closed behavior while
comparing any proposed tuning against a frozen, independently reviewed set.

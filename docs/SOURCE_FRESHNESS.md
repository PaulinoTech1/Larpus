# Offline source freshness detection

The checkout annotates retrieved originals and derived notes with
`provenance.freshness`. This is not active in the frozen production release until
prepared and activated through the updater. The running GPU workload and source
index are not modified by these checks.

Signals distinguish three different questions:

- Reviewed `supersedes`, `corrects` and `conflicts` relationships flag the affected
  predecessor identity. Relationship scope and evidence remain attached. A correction
  to one calculation does not invalidate every claim in the paper.
- A review interval flags `review_due`: 30 days for recognized product pricing/plan
  information, 180 days for recognized operational/security documentation, and 730
  days for general research. Title/URL classification is a heuristic, not a complete
  topic classifier. These are owner curation defaults, not publisher expiry dates.
- Missing dates produce `freshness_unknown`; future dates produce a review signal.
  `no_known_change` means no local warning was found, never certified currency.

An explicit `reviewed_on` date takes priority over revision/publication dates.
Snapshot/download dates never reset the clock. Month/year precision uses the end
of the period for conservative aging, without treating the current month/year as
a future publication. Old mathematical foundations may remain valid despite a
review warning. Fast-changing pricing, security and platform recommendations need
more frequent checking regardless of which persona retrieved them.

Run `python scripts/source-freshness.py` for the private report at
`data/source-freshness.json`. The October 12 local inventory contained 410 records:
241 review candidates, 110 unknown and 59 with no known change. There were no
reviewed lifecycle links in that index; the mechanism does not invent them.

The prompt asks personas to disclose freshness gaps and honor scoped lifecycle
evidence. This is guidance to the model, not a guarantee it will comply. Tests
verify deterministic signals and retrieval compatibility; model behavior needs
separate evaluation. No external publisher polling, semantic contradiction
detector or automatic correction import is implemented. Offline agents cannot
discover a publication that the owner has not yet admitted. Owner-approved refresh
and reviewed lifecycle metadata remain necessary.

# Verified output hold check, 2026-10-27

Release `882c959c3d4540a5ba4b4b89f1596b17`. Route: local HTTP to the live
gateway, verified profile, streaming, output DLP on every released sentence.
Horizon input gate at the 0.5 label boundary. Answers were not stored and
were not scored.

Command: `python scripts/performance_suite.py --run`

Run `8959e76e92274684817ccb135a80dc8c`. Nine warmups and 27 measured
requests. All 36 completed. Measured success was 27/27. Failures: none.
Partial failures: none. No input quarantine, no lexical hold, no output DLP
hold, and no HTTP 422 or 503.

| | Median | p90 | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: |
| First checked text | 5.268 s | 6.924 s | 4.637 s | 7.880 s |
| Completion | 7.021 s | 8.988 s | 4.844 s | 9.055 s |

`cyber-pentest`, the case Horizon blocked on the previous wording, completed
3/3. First text median 5.055 s, p90 5.083 s. Completion median 8.569 s.
Its warmup also completed, first text 10.326 s.

The first warmup, `home-greeting`, took 52.474 s to first text. Later
greeting measurements were 7.880 s, 4.637 s and 4.864 s. That first sample
is excluded from the table above.

Warm stage medians on the 27 measured requests, overlapping clocks: input
94 ms, retrieval 1887 ms, model selection 47 ms, model first frame 742 ms,
isolation preflight 721 ms, MCP connect 967 ms. The assembly scorer was
4 ms. These are not an additive budget.

Receipt: `data/evals/performance/8959e76e92274684817ccb135a80dc8c/summary.md`.
With 27 samples, p90 describes this run only.

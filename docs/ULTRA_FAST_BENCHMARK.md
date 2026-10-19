# Ultra Fast: owner-only model benchmark

This is an explicit application-check bypass experiment, not a production chat
setting. No HUD toggle, public endpoint or MCP bypass tool is added. The normal
gateway, auth, filtering and frozen release are unchanged.

Plan without inference:

```powershell
python scripts/benchmark_ultra_fast.py
```

Run from the owner checkout with the station stopped:

```powershell
$env:TEMP='E:/speedzone_MS/LARPUS/data/tmp'
$env:TMP=$env:TEMP
python scripts/benchmark_ultra_fast.py --run
```

The default is four fixed cases, four measured alternating rounds and one
excluded warmup per case/variant: 40 calls total, 32 measured. Cases cover a
greeting, norms, scalar-ODE pushback and fictional SOC validation. The selected
model, context, GPU residency, persona temperature and output limit are retained.
Only the selected model and agent/retrieval worker are temporarily started; the
gateway and broker remain stopped. The existing offline pod, unprivileged
read-only client, resource limits and setup identity checks remain. No clock,
power, dependency, model or network-binding changes are made.

| Variant | Timed work | Input |
| --- | --- | --- |
| `raw` | Direct local model HTTP request and unscreened stream | Fixed user/history messages, without persona or retrieval context |
| `prepared` | Same direct model path | Persona instructions and retrieved original evidence assembled once beforehand using the selected frozen code |

Inside the timed path there is no LARPUS per-request integrity/isolation
preflight, MCP handshake, inference broker, input/output screening or approved
sentence-release gate. Prepared-input construction still runs normal checks
outside the model timer. System/defense instructions embedded in prepared input
are retained. This does not disable OS/container isolation or the model's own
learned behavior; it is not a claim that every layer of security has disappeared.

`first_text_seconds` measures HTTP request to the first nonempty model content
inside the offline client. It includes model HTTP admission/prefill and excludes
owner process/WSL/client-container startup and prompt preparation. It is an
**unscreened model first token**, not production first approved text.
`total_seconds` is the complete model reply on that same clock;
`owner_elapsed_seconds` also includes launching and collecting the client.
Ollama token counts/durations provide reported generation tokens/second, separate
from first-text time. Warmups, failures and missing measurements are not zeros.

Private run directories under `data/evals/ultra-fast/<id>/` contain complete
unfiltered answers, prepared prompts/evidence, prompt hashes, model identity,
every attempt and an invalid-by-default report. They remain ignored owner data;
do not publish them as source or render them as trusted HTML. No accuracy or
security equivalence is inferred from a faster result. Dropping persona/evidence
can change answer quality; removing screening can expose output production holds.

The owner release lock prevents normal maintenance/model switching during the
window. The benchmark refuses an already-running gateway or nonempty running
container inventory. Cleanup stops the services it started and restores the
original WSL stopped/running state. Unexpected new container activity prevents
pod shutdown/WSL termination rather than killing unrelated owner work. A failed
setup, interrupted run or identity change remains invalid with retained evidence.

No commit, push, candidate activation or change to production defaults is implied
by running this benchmark. Results will be recorded separately from the existing
five-second secure-production plan.

## First measured run: 2026-10-19

Receipt `979c4a67451f454a9871ad195c508e40` completed all 40 calls successfully;
eight warmups were excluded and 16 measured samples remain per variant. The
report is valid, model/selection checks passed and the observed owner source
hashes were unchanged at completion. The selected frozen release remained
`7df2e957751642d6ace4630fa047fe94`. Model size and GPU allocation both reported
20,862,835,097 bytes with context 131072. No CPU/power settings changed.

| Inside-client model measurement | Raw input | Prepared LARPUS input |
| --- | ---: | ---: |
| First nonempty text, median | 1.256 s | 1.807 s |
| First nonempty text, p90 | 1.427 s | 3.112 s |
| First nonempty text, p95 | 1.716 s | 3.198 s |
| Complete response, median | 2.484 s | 3.447 s |
| Complete response, p90 | 3.010 s | 5.036 s |
| Reported generation rate, median | 40.02 tokens/s | 39.37 tokens/s |
| Owner elapsed complete response, median | 2.958 s | 3.968 s |

Per-case first-text medians (four measured samples each):

| Case | Raw | Prepared | Prompt tokens raw / prepared |
| --- | ---: | ---: | ---: |
| Greeting | 0.883 s | 3.047 s | 19 / 3796 |
| Norms | 1.351 s | 0.796 s | 30 / 4900 |
| Scalar ODE | 1.310 s | 2.753 s | 72 / 3952 |
| SOC | 1.097 s | 0.582 s | 45 / 3257 |

Prepared prompt-evaluation durations varied strongly by case/order: measured
greeting/ODE requests reported about 2.29-2.44 seconds, norms/SOC about
0.17-0.29 seconds. Warmup prepared norms initially took 3.366 seconds to first
text. Repetition and model cache behavior therefore matter; the pooled median
does not describe every request or a cold full-context prompt. Cache internals
were not instrumented, so this does not establish the precise cause.

Both variants reached first unscreened text below five seconds in every measured
sample. This establishes a useful model-side observation on four fixed warm
cases, not a production SLO. Persona/evidence preparation and all normal LARPUS
per-request gates are outside or absent from that timer. The older 7.210-second
HTTP production median used eight cases and a different path, so subtracting the
two results would not isolate security overhead or prove an equivalent speedup.
Answers were retained without output filtering; no quality equivalence is claimed.

Cleanup independently recorded no remaining containers, unchanged release
selection and stopped WSL; the Windows gateway was absent and nightly notes
remained Disabled. No production mode, release activation or dependency/image
replacement occurred. Private evidence includes `raw.jsonl`,
`prepared-prompts.json`, `identity-observed.json` and `report.json`.

Validation: 16 focused benchmark/lifecycle tests passed, including retained
partial/interrupt failures, initially running chat refusal, cleanup ownership,
WSL restoration and warmup/failure accounting. The final isolated project suite
passed 414 tests in 132.659 seconds with four documented skips. Complexity
passed without allowance changes; CLI dry-run starts no services. Raw answer and
prepared-prompt files were confirmed ignored by Git. Application runtime, HUD,
deployment pins and frozen payloads were not edited; this feature is owner code
in the working checkout, not a production activation.

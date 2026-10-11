# Persona and model strategy

Decision, 2026-10-11: keep Qwen3.5 27B Q4_K_M as the common model while improving
reliability, retrieval and answer evaluation. No model downloads, replacements,
CPU offload changes or live capability comparisons were performed for this work.

Personas supply role, scope, tone and local skills. These change instructions,
not trained weights. Different Ollama tags or SYSTEM prompts alone are not
proof of different capabilities. Ollama distinguishes SYSTEM customization from
ADAPTER weights: https://docs.ollama.com/modelfile.

The active configuration uses 131,072 context, not the 262,144 target. The loaded
model reported about 21 GB in Ollama placement; actual device allocation includes
other workloads and overhead. Two similarly sized models will not fit together
in the 24 GB GPU. Ollama queues requests and can unload models when capacity is
insufficient: https://docs.ollama.com/faq#how-does-ollama-handle-concurrent-requests.
Switching may incur loading and context-prefill latency. Switching roles with
one loaded model avoids weight replacement, but still requires prompt processing.
Do not promise instantaneous switching or add concurrent GPU loads.

Options:

| Strategy | Benefit | Cost / adoption condition |
| --- | --- | --- |
| One model, scoped personas and retrieval | Consistent deployment, no weight swapping on role change | Domain accuracy still needs evaluation |
| One smaller fast model plus a stronger model, loaded on demand | Potentially quicker casual dialogue | Cold-switch delays, smaller-model quality and context limits need measurement |
| Specialist model for a demonstrated task | Could improve code or mathematical answers | Must beat the baseline; adds model provenance, license, storage and release testing |
| Separate model for every persona | Independent tuning possible | No demonstrated benefit here; multiplies maintenance and evaluation |

Evaluate models by task family rather than by character: conversational latency,
code/Linux reasoning, and mathematical/statistical reasoning are useful candidates.
Use matched held-out questions, relevant local evidence and manual scoring for
correctness, citation support, uncertainty and useful pushback. Record first-text
latency, completion latency, cold switch cost and GPU memory at the same context.
Reject a candidate that improves personality while losing accuracy. Keep voice
on CPU, preserve the chat transcript, and treat summaries as untrusted lossy data.

Live comparisons remain deferred until notes for the current collection finish,
as required by CAPABILITY_TRIALS.md. Existing per-persona model configuration is
an extension point, not evidence that switching models is currently validated.
Every added model must retain offline operation, approved local tags, full GPU
placement checks and the same filtering/DLP boundary.

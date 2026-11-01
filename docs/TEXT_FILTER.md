# Local input filtering

The gateway filters every browser-supplied user and assistant history message
before adding the server-owned system prompt or calling Ollama. Earlier history
cannot bypass the filter by putting payloads in an assistant role. Current history
is still client supplied, not an authenticated transcript; the filter does not
make those messages trustworthy. No model, GPU, cloud API, or network lookup is
used for scanning.

## Layers

1. Existing JSON/body/history/role limits remain enforced.
2. Stegdetect `inspect_text`, `Policy.CONTEXTUAL`, 8000-character/64-finding limits
   inspect original Unicode. Only complete allow decisions with an identical
   forwarding candidate proceed. Review/block/limit/invalid results are held.
3. Larpus rejects hidden controls and format characters, retaining contextual
   emoji joining support; combining runs over 32 characters are held.
4. A bounded NFKC/casefold/whitespace detection view catches a small list of
   explicit instruction overrides and forged model-role markers. Allowed text
   is forwarded unchanged, not silently stripped or rewritten.
5. After the gateway loads `config/horizon.json`, each chat message that has
   already been allowed is classified by the local Horizon snapshot. Six CPU
   threads, a 4,096-token window, and a 64-token overlap cover every token.
   A segment is quarantined when its injection probability is at least 0.5,
   which is the snapshot's own SAFE/INJECTION label. Raising that cutoff to
   0.9 would let injection labels through. On this snapshot, "reproduce the
   finding before accepting it" scored 0.7053. A direct instruction override
   scored 0.9997 and a paraphrase scored 0.9958. The original
   `cyber-pentest` wording scored 0.5336 because it said "without trusting
   its first answer." The same request without that clause scored 0.1529.
   The suite case now says the lab must confirm the finding itself, which
   scored 0.3567 and stays under the 0.5 label. A server-owned coaching
   prefix also pushed the original wording under 0.5, but it lowered the
   paraphrase from 0.9958 to 0.9661, so the prefix was not adopted. Run
   `8b0ab6414c6e49aea7d4dac81a0401ab` recorded the old wording as
   `invalid_protocol` because the runner did not recognize the quarantine
   event. A 0.5 injection label does not stop the gateway. The message text is written
   to the private DLP quarantine as an input incident, removed from the model
   prompt, and removed from the saved transcript. If that message was the new
   question, the HUD stays on the earlier conversation and shows the incident
   id. If it was an older turn, that turn's pair is removed and the new
   question still goes to the model. A missing worker, checksum mismatch,
   incomplete segmentation, or quarantine-write failure still holds the
   request closed. This step does not run for direct `inspect_message`
   callers, so evidence, skills, and voice keep the earlier gate. The
   classifier cannot turn an earlier hold into an allow. Inspect a record
   with `python -m runtime.dlp inspect INCIDENT` and delete it with
   `python -m runtime.dlp delete INCIDENT`. The record is inert text.
6. A server-owned instruction suffix reminds personas that conversation text
   is untrusted. Tool execution stays disabled; enforcement belongs outside
   the model, independent of its answer.

HTTP 422 holds text with a stable reason and zero-based message index. HTTP 503
holds detector failures; missing dependency prevents startup. No scan reports
or raw prompts are logged. There is no “forward anyway” option. Held older
history requires resetting the conversation. Future STT, retrieved files, and
tool output must reuse this gate before reaching the model; those features do
not exist yet. Responses themselves are not semantically validated by this gate.

## Install and rebuild offline

Upstream: https://github.com/PaulinoTech1/Steganography
MIT, pinned commit `ba0fc95a5c8ea256bdf1501de400304837e33c30`.
The Python dependency in `requirements.txt` pins that commit, not floating main.
During online preparation:

```powershell
python -m pip install -r requirements.txt
python -m pip wheel --no-deps -r requirements.txt --wheel-dir data/wheels
```

Copy the wheel cache to the offline PC, then install without network:

```powershell
python -m pip install --no-index --no-deps --find-links data/wheels stegdetect==0.2.0
```

Record the cached wheel's SHA256 and retain upstream MIT license in the artifact.
Do not replace it with an unrelated PyPI wheel with the same version number.
The installed package has no runtime dependencies. Installation/build preparation
may download build tooling; runtime scanning never does.

## Evidence and limits

21 local tests pass, covering gate-before-Ollama rejection, Unicode carriers,
explicit overrides, fullwidth text, history injection, detector error handling,
legitimate multilingual/emoji samples, and a deliberate semantic bypass.
These hand-authored tests do not establish production false-positive/negative
rates or model-level resistance. Ordinary discussions quoting blocked phrases
can be held. Paraphrases, encoding, acrostics, and novel injection techniques can
pass. No encoded payload is decoded here. A successful filter decision means
only that these particular checks allowed the text.

Upstream explicitly limits itself to Unicode carriers; its semantic lexical
experiment is unshipped and is not used here. Larpus's rules are separate local
heuristics, not a claim that upstream gained semantic detection. OpenShell policy
and outbound restrictions remain separate, unverified deployment gates.

[Detection-rate, false-positive/negative and coverage tracking](STEGDETECT_EVALUATION.md) separates synthetic evidence from production claims.

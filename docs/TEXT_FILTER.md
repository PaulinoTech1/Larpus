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
5. A server-owned instruction suffix reminds personas that conversation text
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

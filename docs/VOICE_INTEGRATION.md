# VoiceStudio integration plan

## Source strategy

Keep VoiceStudio as a separately pinned sidecar checkout under ignored `vendor/`,
not copied into MIT modules. After reviewing a release, clone recursively and
record its exact commit and submodule hashes in a deployment manifest. Preserve
upstream LICENSE, notices, lockfiles, and model licenses. No checkout is bundled
in this kickoff. Prefer its documented local backend API through a thin Larpus
adapter; do not embed the full desktop UI just to generate speech. The requested
Tauri reference describes older packaging: current upstream uses Electron and
a Python backend. Pin the chosen version before coding against its routes.

Disable analytics, remote workers, cloud providers, update checks, and automatic
downloads. Inspect the pinned source/config for actual controls; do not invent
environment variables. Start with outbound network blocked and cached models.
Validate runtime with an empty external network route. Installation downloads
are an explicit preparation step, never a wake-word side effect.

## 24 GB model budget (initial candidates, benchmark required)

| Stage | Candidate | Budget / decision |
|---|---|---|
| Language | Ollama `qwen2.5:14b`, default Q4_K_M | about 9 GB weights; reserve 3–5 GB for KV/runtime; 4096 context |
| STT | local Whisper small via CPU implementation | about 244M parameters; use CPU first to leave GPU headroom |
| TTS + clone | VoiceStudio's local OmniVoice engine | measure actual peak VRAM on pinned version; do not assert simultaneous fit |
| Wake word | openWakeWord CPU, locally trained/cached “larpus” detector | separate adapter; VoiceStudio wake-word support is not assumed |

These are proposals, not benchmark results. VoiceStudio's current default model
is `k2-fsa/OmniVoice`; pretrained weights include non-commercial and additional
tokenizer terms. Review each weight license. Use the 64 GB host RAM for STT and
cache. Serialize GPU work: STT → Ollama → unload language model if necessary →
TTS. If latency/memory is poor, try `qwen2.5:7b` by updating persona config and
recording its exact digest. Do not budget all 24 GB for weights. Record measured
peak GPU memory and end-to-end latency before enabling continuous listening.

## Loop and adapter contract

1. Owner explicitly enables listening; visible mic indicator and immediate mute.
2. CPU wake detector consumes an in-memory audio ring; discard pre-wake audio.
3. VAD ends an utterance; max 30 seconds. Local STT returns text and confidence.
4. Show transcript for correction or submit to the same persona/chat API.
5. Animate the torus while the agent produces a response.
6. Local TTS renders text with a selected, consented voice profile; play locally.
7. Return to wake detection. Pause detector during playback to prevent self-wake;
   add echo cancellation and explicit barge-in only after baseline tests.

Proposed internal adapter operations: transcribe WAV → text; synthesize text +
profile → WAV; list local profiles. Map these to verified VoiceStudio routes in
the pinned version. Adapter binds loopback only (reserved 7861); no browser
SpeechRecognition or speechSynthesis because locality is not guaranteed there.
Current mic button invokes a 501 stub and requests no microphone permission.
Dictation later reuses STT without sending until the owner confirms.

Voice profiles stay under `data/voice/profiles`; raw audio retention off by default,
opt-in recordings under `data/voice/recordings`. Clone only voices the owner may
use, keep samples local, and allow profile deletion. Tests before enabling voice:
offline startup, muted mic, false wakes, model missing, device unplugged, oversized
audio, echo/self-trigger, cancellation, and VRAM recovery after an error.

Sources checked 2026-10-07:
- https://github.com/debpalash/VoiceStudio
- https://github.com/debpalash/VoiceStudio/blob/main/LICENSE-NOTICE.md
- https://ollama.com/library/qwen2.5:14b

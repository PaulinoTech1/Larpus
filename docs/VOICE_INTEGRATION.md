# Local voice loop - deployed 2026-10-08; controls updated 2026-10-09

## Using it

Refresh the HUD. Open **VOICE / INPUT & PLAYBACK**, click VOICE and allow
microphone access. The microphone selector lists browser-visible inputs; REFRESH
MICS updates the list after permission or device changes. A selected device uses
an exact device ID rather than silently choosing another microphone. Device IDs
and names are not sent to the server or saved; reselect after a page reload.

Push-to-talk is the default: RECORD, speak, then STOP RECORDING. The transcript
lands in the composer for correction before SEND. Hands-free listening is optional;
review-before-send remains on unless explicitly unchecked. Draft text is preserved
and a transcript is appended rather than replacing it. Empty/no-speech results
never submit chat or execute commands. Nearby speech can still be recognised;
VAD and confidence filtering reduce false triggers but do not prove correctness.

Speak replies is independent of microphone capture, so typed chat can speak with
the microphone off. PAUSE AUDIO / RESUME AUDIO preserves the playback position.
The speed slider adjusts playback from 0.85x to 1.5x while preserving pitch where
supported by the browser. Piper's synthesis length scale is 0.85 (a quicker default
cadence than the previous model default). REPEAT LAST replays the latest reply;
REPLAY REPLY on any displayed assistant message reads that entire reply, including
older replies and text beyond the initial 2000-character spoken preview. Long
replays are synthesised in bounded chunks and may have pauses between chunks.

VOICE toggles capture only; disabling Speak replies stops playback. Capture stays
suspended during playback by default, including paused playback, to reduce feedback.
Optional hands-free interruption uses sustained microphone energy to stop playback
and generation, then capture a new utterance. Headphones are recommended: this
is not acoustic echo cancellation and can misfire on speaker audio. Listening
is opt-in on each page load. No recordings or generated speech are saved to disk.

Exact station commands in optional auto-send mode: "Larpus reset chat", "Larpus
switch to Network Engineer" (or another displayed name), "Larpus repeat", and
"Larpus mute" / "mute voice". In review mode these are ordinary draft text until
the owner chooses the UI action; sending a draft sends a chat message. There are
no OS actions, wake-word detector or voice cloning. Use buttons for commands while
audio is playing, because capture is suspended. Wit comes from persona wording:
natural British English and occasional dry humour, omitted in serious contexts.

Use localhost HTTP on the station or trusted LAN HTTPS on another device.
Microphone permission requires a secure browser context. SpeechRecognition and
speechSynthesis browser services are not used. The browser only captures audio and
plays WAV returned by local processing. Final microphone/speaker and LAN-device
acceptance must be performed on those devices; headless tests do not verify them.

## Implementation and source boundary

VoiceStudio is checked out under ignored vendor/VoiceStudio at commit
06c6e077f0fc35149efefc3561e9be5ae835d916. Its unmodified
backend/engines/_asr_sidecar/main.py transcription adapter is loaded inside a
separate speech worker with an explicitly preloaded local CPU model. The full
VoiceStudio desktop/API, remote workers, galleries and update/analytics machinery
are not run. This is a narrow VoiceStudio ASR integration, not full studio embedding.

Faster Whisper 1.2.1 uses Systran/faster-whisper-small.en with CPU int8.
Piper TTS 1.8.0 uses rhasspy/piper-voices en_GB-alan-medium (British English).
Wit comes from role-specific persona instructions, not the voice model.
Both run on CPU so Ollama retains the GPU. The worker uses validated PCM arrays
for recognition, avoiding PyAV 19's incompatible decoding keyword. Models are
loaded per operation; startup overhead remains. A trusted wrapper enables local
VAD, deterministic decoding, no previous-text conditioning and segment confidence
filters beneath the unmodified pinned VoiceStudio adapter. Digital silence is
rejected before loading the ASR model.

```text
Opt-in mic -> mono 16 kHz PCM16 WAV -> offline VoiceStudio/Faster Whisper adapter
  -> transcript -> exact UI command OR selected persona through isolated MCP
  -> output DLP -> approved text -> offline Piper -> WAV playback
```

Only DLP-approved generated replies reach automatic TTS. Held replies return an
incident instead. Command confirmations are fixed application text. The authenticated,
rate-limited replay route accepts bounded text and applies the local input filter
and output DLP again before synthesis; it is not a trusted model-output bypass. Replies longer than 2000 characters speak an initial portion
and indicate the remainder is displayed. Text still works if synthesis fails.
Utterances are at most 30 seconds. Audio is browser/process memory only; runtime
does not save recordings or generated speech. No prompt/audio logs are enabled.

## Worker ports, mounts and limits

larpus-voice is a separate rootless Podman container, network=none, with no
published ports and stdio requests only. User 1000:1000, read-only image,
capabilities dropped, no-new-privileges, no GPU/host devices, 4 GiB RAM, 8 CPUs,
128 PIDs, log-driver=none. /tmp is a 128 MiB noexec/nosuid/nodev tmpfs.
Its only bind is /home/larpus/voice-models -> /models read-only. It has no owner
home, Windows drives, credentials, sockets, model-service route or quarantine.
The gateway checks actual image, source hash, OCI privileges, network and mounts
before operations. Health reports the worker's boundary separately from Ollama.
Private image pins and model SHA256 records are in ignored data/voice-deployment.json
and data/voice-model-hashes.json. These are local receipts, not runtime model-file
integrity checks against a compromised owner/kernel.

## Prepare and rebuild

The dedicated WSL distro, rootless Podman and cached pinned Python base described
in WINDOWS-HOME-ISOLATION.md are prerequisites. Explicit online preparation:

```powershell
python scripts/setup-voice.py prepare
```

This downloads public dependencies/weights without accounts or user audio. It
requires the pinned VoiceStudio checkout (inspect/check out the documented commit
if your clone differs). Existing wheel/model caches remain in /home/larpus.
Record/cache all transitive wheels and model hashes; upstream tags can change.
Offline build/start:

```powershell
python scripts/setup-voice.py deploy
```

Existing worker replacement is refused. Stop/review only larpus-voice before
removing that container to rebuild; preserve models and quarantine. Export/transfer
and reseal the main runtime after gateway/persona changes, then restart the gateway.
After Windows shutdown, start the main pod plus the voice container:

```powershell
wsl --distribution Larpus --user larpus --exec env XDG_RUNTIME_DIR=/run/user/1000 podman pod start larpus-offline
wsl --distribution Larpus --user larpus --exec env XDG_RUNTIME_DIR=/run/user/1000 podman start larpus-voice
python -m runtime.isolation check
.\scripts\start-lan.ps1
```

## Validation and licensing

Real British TTS generated a WAV and local ASR transcribed it in the network-disabled
worker; the name Larpus was heard as Lapis. Negative internet/LAN connection probes,
loopback-only networking and absent owner-drive/quarantine checks passed. Tests
cover malformed/oversized/truncated WAV, unavailable worker and DLP-held replies
never invoking TTS. Browser microphone/playback, false triggers, ambient noise,
permission denial, device removal and second-device use still need owner acceptance.

VoiceStudio's adapter and license are included in the private worker image;
its source remains a pinned external checkout. AGPL-3.0 obligations apply to
redistribution/integration and modified network use; retaining a sidecar does not
waive them. Piper is GPL-3.0; model weights have separate terms (the cached MODEL_CARD
is authoritative for the selected voice). Keep source/notices and review the
combined distribution before publishing images. The repository retains its MIT
license; this does not relicense bundled third-party software.

Sources: https://github.com/debpalash/VoiceStudio,
https://github.com/SYSTRAN/faster-whisper,
https://github.com/OHF-Voice/piper1-gpl,
https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/alan/medium.

## Voice controls validation (2026-10-09)

The HUD now streams approved sentences into a FIFO speech queue while generation
continues, with at most one WAV prepared ahead. See [streaming](STREAMING.md) for
inspection boundaries, interruption handling and validation. The complete-WAV
behavior described for the original chat API remains available to API callers.

52 Python tests pass, including uncertain-segment rejection, empty transcription
and replay text/DLP checks. `node tests/voice-ui.cjs` verifies exact mic selection,
silence and review gates, paused-playback capture suppression, resume position,
speed changes, replay with the microphone off, older-reply synthesis and cancellation.
These simulated browser tests do not prove physical microphone accuracy or sound
quality. A real offline Piper -> Whisper test reproduced the synthetic sentence,
and one second of digital silence returned no speech. The test WAV was 4.9 seconds
long and generated in about 2.5 seconds on this machine; this is not a benchmark
for arbitrary replies. Physical mic, room noise and speaker acceptance remain owner
checks. Both worker images were rebuilt offline; previous containers remain stopped
for rollback, with credentials, models and quarantine preserved.

The matching [offline scan receipt](VOICE-CONTROLS-SCAN-RECEIPT.json) records 64 clean skill scans and eight retained MCP findings (MEDIUM aggregate risk). Overall health remains degraded for those warnings; static scanning is not a full audit of voice quality or browser behaviour.

## Persistent CPU worker candidate

The release workflow builds a separate voice container from the already cached,
pinned voice image with no network access or dependency changes. Piper and Whisper
load lazily once and remain in that worker. The client uses bounded length-prefixed
JSON over a mode-0600 Unix socket entirely inside the network-disabled container;
there is no additional host port or writable host mount. Voice remains CPU-only.
The per-release voice-deployment.json is pinned by the release receipt; legacy
releases retain the original worker and profile for rollback.

HUD timing reports request and worker duration, model-cache status, and first
browser playback event. These do not measure physical speaker latency or
recognition accuracy. Paused playback retains its position; STOP cancels queued
audio and browser generation requests. In-flight CPU synthesis may finish before
the worker accepts another request.

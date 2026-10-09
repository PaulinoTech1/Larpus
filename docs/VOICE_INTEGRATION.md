# Local voice loop ? deployed 2026-10-08

## Using it

Refresh the HUD and select Home assistant for dry, gentle wit in British English.
Click VOICE and allow microphone access. Speak, then pause for about one second.
The transcript appears as your chat message; the selected persona answers in text
and speech. Click VOICE again to immediately stop capture/playback. Listening is
opt-in on each page load. Capture pauses during transcription, inference and speech
playback to reduce self-triggering. Browser echo cancellation is requested.

Exact station commands: "Larpus reset chat", "Larpus switch to Network Engineer"
(or another displayed persona name), and "Larpus mute" / "mute voice". Fixed
confirmations are spoken; no arbitrary OS action or shell execution is enabled.
Speech recognition can mishear names. Use the selector/button when needed.
Listening is speech/silence segmentation, not wake-word detection; nearby speech
may be submitted while listening is enabled. Continuous listening must be explicitly
enabled. No voice cloning or wake-word model is deployed.

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
Wit comes from the home-assistant persona instructions, not the voice model.
Both run on CPU so Ollama retains the GPU. The worker uses validated PCM arrays
for recognition, avoiding PyAV 19's incompatible decoding keyword. Models are
loaded per operation; real-device latency tuning remains future work.

```text
Opt-in mic -> mono 16 kHz PCM16 WAV -> offline VoiceStudio/Faster Whisper adapter
  -> transcript -> exact UI command OR selected persona through isolated MCP
  -> output DLP -> approved text -> offline Piper -> WAV playback
```

Only DLP-approved generated replies reach TTS. Held replies return an incident
instead. Command confirmations are fixed application text. No arbitrary-text TTS
endpoint is exposed. Replies longer than 2000 characters speak an initial portion
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

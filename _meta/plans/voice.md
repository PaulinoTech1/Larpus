# Local voice loop
Goal: opt-in microphone listening and spoken persona replies, fully local.
Constraints: no browser cloud speech; preserve isolated LLM and DLP before TTS.
Input: bounded PCM WAV; output: transcript and synthetic WAV.
Done when: real transcription/synthesis, network-disabled worker and mute/error tests pass; microphone/speaker acceptance remains owner check.
Choice: dedicated rootless CPU worker, VoiceStudio pinned ASR adapter + Faster Whisper small.en + Piper British English.
Rejected: full VoiceStudio all-engine desktop backend (large dependencies); browser SpeechRecognition (locality not guaranteed).
Listening: visible opt-in, silence segmentation, bounded utterances; pause during reply/playback. Push-to-talk fallback.
Actions: awaiting owner's scope; default only exact Larpus UI commands. No arbitrary OS commands.
No new commit/push authorization this turn.
AgentDB command unavailable in this environment; repo inspection used instead.

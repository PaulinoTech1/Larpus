# Public checkout CI scope

Owner-approved boundary: GitHub-hosted runners may use public repository source, public dependencies and authored synthetic fixtures. LARPUS inference, speech, retrieval data and owner services remain local. CI does not require the owner's password, GitHub archive token, TLS keys, original corpus or running station.

## Checks that earn their cost

| Check | What a pass establishes | What it does not establish |
| --- | --- | --- |
| Tracked-file boundary | Known private paths/weight/key/index patterns are absent from tracked files | Secret-content detection or protection after an accidental public push |
| Complexity gate | Owned Python metrics stay within reviewed allowances | Good design or runtime deadlock freedom |
| Isolated Python suite | Public contracts pass using synthetic index and test fixtures | Real WSL/Podman/GPU isolation, reboot safety or private corpus correctness |
| Nine Node suites | Streaming, context, voice controls, teaching, memory, diagnostic IDs, speech-text, model-switch and session recovery logic pass | Rendered accessibility, physical microphone, room noise or cross-device acceptance |
| Broker prompt hashes | Authored prompt templates match the committed approval manifest | Uncompromised runtime callers or semantic injection immunity |
| Companion catalog | Scenarios/personas/skills meet authored catalog contracts | Actual model expertise or source-grounded answer quality |
| Stegdetect evaluation | Synthetic classification accounting executes with explicit denominators and gaps | Production detection/FPR/FNR estimates or a required perfect score |

CI does not install models, ONNX weights, voice libraries, CUDA, Podman, OpenShell or SkillSpector. It does not invoke release stage/prepare/activate/start, a GPU benchmark, a live broker harness, repository archive downloads or an owner nightly writer. Real static scans, source-pinned warning review and live isolation/readiness remain release-preparation gates. Detector evaluation intentionally reports misses; tests verify accounting rather than forcing the synthetic miss rate to zero.

## Workflow contract

`.github/workflows/public-checks.yml` runs on pull requests, pushes to main and manual dispatch. Two jobs cover Ubuntu 24.04 and Windows 2025 with Python 3.10 (gateway compatibility) and Node 24 (HUD logic). Each has a 15-minute ceiling. New runs cancel older runs for the same ref; matrix failures do not cancel the other OS.

Actions are full-commit-SHA pinned to verified upstream action refs, with `contents: read` only and checkout credential persistence disabled. No repository secrets, write permissions, self-hosted owner runner, deployment environment, artifact upload, dependency cache, `pull_request_target` or privileged workflow chain is configured. Logs contain public test output and synthetic counts; no private source/database is present on hosted runners. Do not add owner-side data or tokens to make a failing test pass. Hosted runners and public dependency installation have internet access: this is not an offline or hermetic build and does not give deployed agents internet access.

`requirements-ci.txt` reuses the existing pinned runtime and document-preparation requirements plus NumPy 2.2.6 for a retrieval contract. Stegdetect remains pinned to its exact upstream Git commit. Python/Node major versions and transitive dependencies are not a full hash-locked toolchain; drift can reveal compatibility failures. Adding a lockfile or broader matrix should be justified by failures, not done as a side effect of a runtime update.

No GitHub run, required branch-protection check or hosted Linux acceptance is claimed until this workflow is committed/pushed and its run completes. Repository settings are unchanged. Public source execution on hosted runners is not certification of safe code; the owner's PC never becomes a PR runner.

## Reproduce locally

From the repository directory, use a separate environment; never replace shared station/scanner dependencies:

```powershell
python -m venv data/ci-env
data/ci-env/Scripts/python.exe -m pip install -r requirements-ci.txt
data/ci-env/Scripts/python.exe scripts/ci.py
```

Node 24 and Git must be on PATH. The runner stops on the first failing command and preserves its nonzero exit. `python scripts/ci.py --inventory-only` checks the tracked-file boundary without importing model/runtime dependencies. The suite builds a temporary synthetic index; ignored private documents, credentials and model files are not copied into that fixture. Temporary loopback test servers are test fixtures, not production listeners.

Workflow review should confirm triggers, least-privilege permissions, full SHA pins, fixed commands and data boundaries before merge. If additional tools need credentials, deployment, private corpus or GPU access, design a separate scoped owner workflow rather than expanding this one silently. Local repro does not upload reports; its ignored reports are development data.

## Validation of this initial workflow

A separate Windows Python 3.10 environment installed only `requirements-ci.txt` and ran `scripts/ci.py` successfully: 222 Python tests (two skips), the then-current seven Node suites, approved broker prompt hashes, companion catalog and Stegdetect report. The initial rehearsal failed because NumPy was undeclared; the declared 2.2.6 dependency corrected it. YAML parsing and explicit trigger/permission/action-SHA controls were checked locally. Neither hosted runner has executed this checkout yet; a green GitHub result and required branch protections remain unverified. The active gateway/model/voice and nightly writer were kept running throughout, with no dependency replacement or deployment.

UI suites are enumerated once in `scripts/ui_checks.py` and used by both CI and owner release preparation. The model-switch and in-page reauthentication suites are included; the earlier seven-suite validation above is historical.

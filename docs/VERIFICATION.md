# Kickoff verification — 2026-10-07

- `python -m unittest discover -s tests -v`: 15 tests passed. Real loopback HTTP
  handlers exercised with mocked inference: persona injection, body validation,
  length boundaries, upstream failures, busy lock, host/origin rejection, static
  asset serving/traversal rejection, health states, voice stub, password gate,
  login cookies/logout, session expiry, login/API limits, and LAN client scope.
- `node --check web/app.js` and `node --check web/login.js`: passed.
- `npm audit`: zero vulnerabilities after updating to KaTeX 0.19.0.
- Host gateway serves the HTML, persona API, health API, and local KaTeX assets.
- Live Ollama query at 127.0.0.1:11434 timed out; Ollama and Podman commands are
  not installed here. No live model, GPU-fit, voice, or sandbox claim is made.
- Browser inspection was attempted with the available computer-use tool, which
  returned “No browser is available.” Rendered visual QA at 375/768/1440,
  keyboard navigation, reduced motion, and full UI chat interaction remain unrun.
  CSS contains those responsive breakpoints; source inspection is not visual QA.

Owner acceptance: start Ollama with the configured local model, open localhost,
send a message, switch personas and confirm history reset, test the microphone
stub, and check the reactor in idle/thinking/error and reduced-motion states.
OpenShell/rootless Podman and voice acceptance gates are in DEPLOYMENT.md and
VOICE_INTEGRATION.md. Mock tests do not establish offline egress isolation.

# Third-party and integration notice

The optional developer scanner NVIDIA SkillSpector is Apache-2.0, pinned separately
in requirements-scanner.txt. Preserve its license and each dependency's notices
when distributing a cached scanner environment. Qwen candidates have model-specific
licenses; consult the exact downloaded weights, independently of Larpus's MIT license.

The existing MIT LICENSE covers Larpus-authored source, not all future bundled
components. KaTeX is MIT; `npm run vendor` copies its license to `web/vendor/katex`.
Stegdetect is an MIT dependency from PaulinoTech1/Steganography, pinned in
requirements.txt. Preserve its upstream license when redistributing cached wheels.
MCP Python SDK 2.3.0 is MIT; its resolved dependencies retain their own licenses.
Preserve their notices when distributing an offline wheel cache or application.
VoiceStudio remains an external optional dependency, AGPL-3.0-only, with its own
copyright and source obligations. Embedding/copying its code needs a license
review of the combined work; preserve full upstream LICENSE and notices when
redistributing. Personal use does not remove obligations on later distribution
or network access to modified versions. Voice and language model weights retain
their own licenses. Do not treat the app license as permission for every model.

Upstream source: https://github.com/debpalash/VoiceStudio/blob/main/LICENSE-NOTICE.md

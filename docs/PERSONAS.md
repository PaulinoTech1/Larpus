# LARP personas

Choose a persona in the HUD selector. Alongside Home Assistant and IT / cyber
LARP Coach, the station includes Linux Kernel Expert, System Administrator,
Network Engineer, Cryptographer, Mathematician, Quantum Mechanics Professor,
Statistician, Economist, Sociologist and Psychologist.

Each role is a local JSON configuration in agents/personas with a distinct
educational prompt, the installed qwen2.5:14b model, and five dedicated locally
authored skills listed in the [role skill catalog](ROLE_SKILLS.md), alongside
its preserved shared skills. Roles support guided practice and
scenario preparation. They do not confer credentials or add system access.
The Psychologist role is educational roleplay rather than clinical care.

Persona edits require rebuilding the sealed runtime and restarting the gateway;
the isolation source fingerprint prevents running mismatched configurations.

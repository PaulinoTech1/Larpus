# Local GitHub repository files

The owner authorised downloading every repository owned by the authenticated
`PaulinoTech1` account. The authenticated REST listing checks the account identity
and follows all pages, including private repositories. This is owner-side read
access; the running LLM receives no GitHub credentials or internet connection.

## Files on the owner PC

- `data/github/mirrors/NAME.git`: full bare Git mirrors, including advertised
  branches/tags/history, checked with `git fsck --full`. Push URLs are disabled.
- `data/github/files/NAME/COMMIT/`: inert default-branch tracked file snapshots.
  These are remote commits, not unsaved or uncommitted work in other local trees.
- `data/github/inventory.json`, `archive.json`: private account inventory, source
  commits and per-file SHA-256/blob IDs. `screening.json` records exclusions.
- `knowledge/github-manifest.json`: ignored pin for the complete private archive
  manifest; the main index manifest records a combined archive hash, not the list
  of private repository names. The read-only SQLite index includes approved text.

The first download contained 22 repositories, including two private ones, and
19,534 materialised files (416,186,199 bytes). Another 200 tracked paths have
Windows-incompatible filenames, including colons in evidence timestamps. Those
files remain in the full Git mirrors; they were not lost or silently renamed.
No LFS pointer files were found in the materialised snapshots. Submodule targets,
GitHub issues, release assets, wikis and other GitHub services are not included
unless their contents are tracked in the repository itself. A Git mirror is not
a complete backup of every GitHub service.

No downloaded project is built, installed or executed. Mirrors use an empty
hook/template directory, HTTPS-only transport and no recursive submodule or LFS
checkout. File extraction reads Git blobs directly without checkout filters.
Existing owner-side Windows Git Credential Manager supplies authentication;
tokens are not printed, saved in the archive, passed as command arguments or
copied into the runtime. GitHub API redirects are refused.

## What Larpus can read

Every persona can retrieve screened source/documentation from the shared local
index. The catalogue lists all repositories. Repository names in GitHub/repository
questions scope retrieval to the named projects; comparisons reserve evidence for
each named repository. Up to three excerpts fit the existing context budget.
Repository citations identify source commit, filename and passage offset.

Text files are UTF-8, at most 256 KiB each, with at most 1,500 accepted passages
per repository. READMEs/documentation are considered first. Binaries, dependencies,
build output, environment/key files and downloaded agent prompts/skill directories
are excluded. Whole-file DLP checks reject recognised credentials, private paths,
addresses and protected values before text chunking. Accepted chunks also pass
the existing Unicode/steganography/instruction-override filter. A scanner failure
or changed source checksum aborts the rebuild. Output DLP remains enabled.

These deterministic checks have false positives and detection gaps; they do not
prove arbitrary source files contain no secrets or prompt attacks. Excluded files
remain available only in the owner archive. Downloaded `AGENTS.md`, `SKILL.md` and
similar instructions never become installed skills or authority over Larpus.
Source retrieval does not grant file execution, arbitrary filesystem access or
GitHub write access. Private repository text is available to the same single-user
station and authenticated LAN interface as the rest of the approved library.

Try: “List all my GitHub repositories,” “Explain my JML- repository architecture,”
or “Find relevant source in my DMARC-Aggregate-Reader repository.” An overview may
be incomplete when its README was excluded; inspect the cited original rather
than treating a generated summary as a code audit.

## Owner refresh

From this working checkout, with existing GitHub credentials in Windows GCM:

```powershell
python scripts/github_archive.py
python scripts/prepare-knowledge.py --reuse-research
python scripts/releases.py stage
python scripts/releases.py prepare ID
python scripts/releases.py activate ID
```

The archive command refuses another account's credentials and retains the
previous index pin if a repository fails. `--use-inventory` uses an existing
owner-reviewed inventory instead of refreshing the account listing; it does not
establish that the list is current. Authentication failures require owner-side
Git/GCM sign-in, never pasting a token into the Larpus chat.

Keep production running during download, screening and preparation. Activation
uses the [brief drain/switch and rollback workflow](UPDATES.md). No periodic network
sync or new port, volume mount, cloud model or remote MCP tool is introduced.
Archive originals and private reports are ignored by Git; do not commit them.

## Owner attribution (2026-10-09)

The owner explicitly identifies the 22 archived PaulinoTech1 repositories as their
work. The shared evidence instructions tell every persona to attribute these
projects to the owner, rather than to LARPUS. This owner declaration is separate
from downloaded reference data. It does not assert sole authorship of every file:
named contributors, upstream projects, dependencies and licenses retain their
attribution. Repository ownership is not evidence of production experience or
permission to disclose private source. Existing screening, DLP and isolation apply.
The snapshots are dated archives and do not include newer uncommitted changes.

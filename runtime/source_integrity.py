"""Fresh source hashing only; no scanner, MCP or process initialization."""
import hashlib
from pathlib import Path

def fingerprint(root: Path) -> str:
    paths=list((root/'runtime').glob('*.py'))+list((root/'skills').rglob('*'))+list((root/'agents/personas').glob('*.json'))
    paths += list((root/'runtime/native').glob('*'))
    paths += [root/'scripts/offline_skillspector.py',root/'scripts/protect-quarantine.ps1',root/'config/dlp.json',root/'config/models.json',root/'config/mcp-capabilities.json',root/'config/mcp-approved.json']
    paths += [root/'scripts/run-isolated.ps1',root/'scripts/export-isolation-source.ps1',root/'scripts/transfer-isolation-source.py',root/'scripts/setup-voice.py']+list((root/'deploy/windows-home').rglob('*'))+list((root/'deploy/voice').rglob('*'))
    paths += [root/'.containerignore',root/'.gitattributes',root/'config/isolation.json',root/'config/inference-broker.json',root/'config/broker-prompts.json',root/'scripts/broker-prompts.py',root/'config/mcp-scan-reviewed.json']
    paths += [root/'knowledge/manifest.json',root/'knowledge/sources.json',root/'knowledge/provenance.json',root/'knowledge/authors.json',root/'config/source-relationships.json',root/'scripts/source-provenance.py',root/'scripts/prepare-knowledge.py']
    paths += [root/'scripts/test-local.py',root/'requirements-knowledge.txt']+list((root/'knowledge/briefs').glob('*.txt'))
    paths += [root/'scripts/releases.py',root/'scripts/complexity.py',root/'config/complexity-baseline.json',root/'config/system-map.json']
    paths += [root/'scripts/evaluate-companion.py']+list((root/'evals').glob('*.json'))
    paths += [root/'scripts/github_archive.py',root/'knowledge/github-manifest.json']
    paths += [root/'config/cpu-retrieval.json',root/'knowledge/embeddings-manifest.json',root/'scripts/prepare-retrieval.py',root/'requirements-retrieval.txt']
    digest=hashlib.sha256()
    for path in sorted({p for p in paths if p.is_file()}):
        if '__pycache__' in path.parts:
            continue
        if path.is_symlink():
            raise ValueError('Symlink in security scan scope')
        raw=path.read_bytes()
        if len(raw)>1_000_000:
            raise ValueError('Oversized security artifact')
        digest.update(str(path.relative_to(root)).replace('\\','/').encode()+b'\0'+raw+b'\0')
    return digest.hexdigest()

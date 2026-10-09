"""Run tests in an isolated project copy without private documents or credentials."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory(prefix='larpus-tests-') as temporary:
        workspace=Path(temporary)
        for directory in ('runtime','agents','skills','config','scripts','deploy','tests','web'):
            shutil.copytree(ROOT/directory,workspace/directory,ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('.containerignore','.gitattributes','LICENSE','LICENSE-NOTICE.md','requirements.txt','requirements-knowledge.txt'):
            shutil.copyfile(ROOT/name,workspace/name)
        library=workspace/'knowledge';library.mkdir()
        shutil.copyfile(ROOT/'knowledge/sources.json',library/'sources.json')
        # Public authored briefs exercise the production retrieval path; private
        # PDF contents/index and all owner data stay outside the test workspace.
        rows=[]
        catalog=json.loads((library/'sources.json').read_text(encoding='utf-8'))
        for entry in catalog['documents']:
            if entry.get('kind')!='reviewed-local-brief':continue
            text=(ROOT/'knowledge/briefs'/(entry['id']+'.txt')).read_text(encoding='utf-8')
            for role in entry['roles']:rows.append((entry['id'],entry['title'],entry['url'],entry['reviewed_on'],'test brief',text,role))
        database=library/'approved.sqlite'
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE VIRTUAL TABLE chunks USING fts5(source_id UNINDEXED,title,url UNINDEXED,snapshot UNINDEXED,locator UNINDEXED,text,role UNINDEXED,tokenize='porter unicode61')")
            connection.executemany('INSERT INTO chunks VALUES (?,?,?,?,?,?,?)',rows)
        connection.close()
        (library/'manifest.json').write_text(json.dumps({'version':1,'database_sha256':hashlib.sha256(database.read_bytes()).hexdigest(),'database_bytes':database.stat().st_size}),encoding='utf-8')
        env=os.environ.copy();env.update(PYTHONUTF8='1',LARPUS_ISOLATION='host')
        result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=workspace,env=env)
        return result.returncode

if __name__=='__main__':raise SystemExit(main())

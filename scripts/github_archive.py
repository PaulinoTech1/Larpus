"""Owner-only GitHub archive and screened index input; never a runtime tool."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/'data/github'
PIN=ROOT/'knowledge/github-manifest.json'
OWNER='PaulinoTech1'
MAX_TEXT=256*1024
MAX_CHUNKS=1500
TEXT_EXT={'.md','.txt','.rst','.py','.ps1','.psm1','.psd1','.js','.jsx','.ts','.tsx','.c','.h','.cpp','.hpp','.rs','.go','.sh','.json','.toml','.yaml','.yml','.css','.html','.sql','.ini','.conf'}
SKIP_DIRS={'.git','node_modules','vendor','dist','build','.next','.venv','venv','coverage','__pycache__','.agents','.claude','.codex','.opencode','.cursor','skills','prompts'}

def stamp():return datetime.now(timezone.utc).isoformat()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');temp.replace(path)

def safe_name(name):
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}',name) or name.endswith('.'):
        raise ValueError('Invalid repository name')
    return name

def safe_file(name):
    path=PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(p in ('.','..') or p.endswith((' ','.')) or re.search(r'[<>:"\\|?*\x00-\x1f]',p) or p.casefold()=='.git' or re.fullmatch(r'(?i)(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',p) for p in path.parts):
        raise ValueError('Unsafe snapshot filename')
    return path

def environment():
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never',GIT_LFS_SKIP_SMUDGE='1',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=str(STORE/'empty-git-config'))
    return env

def command(*args):
    return ['git','-c','credential.helper=manager','-c','core.hooksPath='+str(STORE/'empty-hooks'),'-c','protocol.allow=never','-c','protocol.https.allow=always','-c','http.followRedirects=false','-c','gc.auto=0','-c','maintenance.auto=false',*map(str,args)]

def git(*args,timeout=900,input=None):
    result=subprocess.run(command(*args),input=input,capture_output=True,env=environment(),timeout=timeout)
    if result.returncode:raise RuntimeError('Git operation failed ('+str(result.returncode)+'); credentials/output withheld')
    return result.stdout

def inventory():
    # Credential stays in this process memory; never printed, written or passed
    # to the model. Existing Windows Git Credential Manager supplies it.
    values=dict(line.split('=',1) for line in git('credential','fill',input=b'protocol=https\nhost=github.com\n\n',timeout=30).decode().splitlines() if '=' in line)
    token=values.get('password')
    if not token:raise ValueError('No existing GitHub credential available')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args):raise ValueError('GitHub API redirect refused')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def get(path):
        request=urllib.request.Request('https://api.github.com'+path,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Larpus-Owner-Archive'})
        with opener.open(request,timeout=30) as response:
            raw=response.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:raise ValueError('Oversized GitHub inventory')
        return json.loads(raw)
    if get('/user')['login'].casefold()!=OWNER.casefold():raise ValueError('Credential belongs to another GitHub owner')
    entries=[];seen=set()
    for page in range(1,101):
        batch=get('/user/repos?affiliation=owner&per_page=100&page='+str(page))
        for item in batch:
            if item['owner']['login'].casefold()!=OWNER.casefold():raise ValueError('Unexpected repository owner')
            name=safe_name(item['name'])
            if name.casefold() in seen:raise ValueError('Duplicate repository inventory; retry listing')
            seen.add(name.casefold())
            entries.append({'name':name,'full_name':OWNER+'/'+name,'clone_url':'https://github.com/'+OWNER+'/'+name+'.git','default_branch':item['default_branch'],'visibility':item['visibility'],'description':item.get('description') or ''})
        if len(batch)<100:break
    else:raise ValueError('Repository pagination limit reached')
    token=None;values.clear()
    return {'version':1,'owner':OWNER,'listed_at':stamp(),'source':'authenticated GitHub REST owner affiliation, all pages','repositories':entries}

def snapshot(repo):
    name=safe_name(repo['name']);url='https://github.com/'+OWNER+'/'+name+'.git'
    if repo['full_name']!=OWNER+'/'+name or repo['clone_url']!=url:raise ValueError('Repository identity mismatch')
    mirror=STORE/'mirrors'/(name+'.git')
    if mirror.is_symlink() or mirror.resolve()!=STORE.resolve()/'mirrors'/(name+'.git'):raise ValueError('Redirected mirror path')
    if mirror.exists():
        if git('--git-dir',mirror,'config','--get','remote.origin.url').decode().strip()!=url:raise ValueError('Unexpected mirror remote')
        git('--git-dir',mirror,'fetch','origin')
    else:
        mirror.parent.mkdir(parents=True,exist_ok=True)
        git('clone','--mirror','--template='+str(STORE/'empty-hooks'),'--',url,mirror)
    git('--git-dir',mirror,'config','remote.origin.pushurl','DISABLED')
    git('--git-dir',mirror,'fsck','--full','--no-dangling')
    branch=repo['default_branch']
    if not isinstance(branch,str) or not branch or branch.startswith('-'):raise ValueError('Invalid default branch')
    try:commit=git('--git-dir',mirror,'rev-parse','--verify','refs/heads/'+branch+'^{commit}').decode().strip()
    except RuntimeError:
        refs=git('--git-dir',mirror,'for-each-ref').strip()
        if refs:raise
        return {**repo,'status':'empty','files':[],'skipped':[],'snapshot_at':stamp()}
    if not re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}',commit):raise ValueError('Invalid source commit')
    dest=STORE/'files'/name/commit
    if dest.is_symlink() or dest.resolve()!=STORE.resolve()/'files'/name/commit:raise ValueError('Redirected snapshot path')
    dest.mkdir(parents=True,exist_ok=True)
    tree=git('--git-dir',mirror,'ls-tree','-rlz',commit)
    files=[];skipped=[];seen=set()
    process=subprocess.Popen(command('--git-dir',mirror,'cat-file','--batch'),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=environment())
    try:
        for record in tree.split(b'\0'):
            if not record:continue
            meta,rawname=record.split(b'\t',1);mode,kind,oid,size=meta.split()
            try:
                filename=rawname.decode('utf-8');relative=safe_file(filename)
                if filename.casefold() in seen:raise ValueError('Case-colliding filename')
                seen.add(filename.casefold())
                if mode not in (b'100644',b'100755') or kind!=b'blob':raise ValueError('Symlink or submodule, retained in mirror only')
                target=dest.joinpath(*relative.parts)
                if target.resolve()!=dest.joinpath(*relative.parts).absolute():raise ValueError('Redirected snapshot file')
                if target.exists() and target.is_symlink():raise ValueError('Snapshot symlink')
                target.parent.mkdir(parents=True,exist_ok=True)
                process.stdin.write(oid+b'\n');process.stdin.flush()
                header=process.stdout.readline().split()
                if len(header)!=3 or header[0]!=oid or header[1]!=b'blob' or header[2]!=size:raise RuntimeError('Unexpected Git object')
                remaining=int(size);sha=hashlib.sha256()
                temp=STORE/'temporary'/uuid.uuid4().hex
                temp.parent.mkdir(exist_ok=True)
                with temp.open('wb') as output:
                    while remaining:
                        block=process.stdout.read(min(remaining,128*1024))
                        if not block:raise RuntimeError('Truncated Git object')
                        output.write(block);sha.update(block);remaining-=len(block)
                if process.stdout.read(1)!=b'\n':raise RuntimeError('Invalid Git object framing')
                temp.replace(target)
                files.append({'path':filename,'bytes':int(size),'sha256':sha.hexdigest(),'blob':oid.decode()})
            except (ValueError,UnicodeError) as exc:
                skipped.append({'path':rawname.decode('utf-8',errors='replace'),'reason':type(exc).__name__})
    finally:
        process.stdin.close();process.stdout.close();process.wait(timeout=15)
    if process.returncode:raise RuntimeError('Git object reader failed')
    git('--git-dir',mirror,'update-ref','refs/larpus-snapshots/'+commit,commit)
    return {**repo,'status':'downloaded','commit':commit,'snapshot_at':stamp(),'files':files,'skipped':skipped}

def sync(refresh=True):
    STORE.mkdir(parents=True,exist_ok=True);(STORE/'empty-hooks').mkdir(exist_ok=True);(STORE/'empty-git-config').write_text('')
    listing=inventory() if refresh else read(STORE/'inventory.json')
    write(STORE/'inventory.json',listing)
    report={'version':1,'owner':OWNER,'prepared_at':stamp(),'inventory_source':listing.get('source','connected GitHub owner inventory'),'repositories':[]}
    for repo in listing['repositories']:
        try:entry=snapshot(repo)
        except Exception as exc:entry={**repo,'status':'failed','error':type(exc).__name__}
        report['repositories'].append(entry)
        write(STORE/'archive.json',report)
        print(repo['name']+': '+entry['status'],flush=True)
    if any(r['status']=='failed' for r in report['repositories']):raise ValueError('Some repositories failed; previous index pin retained')
    write(PIN,{'version':1,'archive_sha256':digest(STORE/'archive.json'),'prepared_at':report['prepared_at'],'repositories':len(report['repositories'])})

def eligible(filename):
    p=PurePosixPath(filename);name=p.name.casefold()
    return not any(x.casefold() in SKIP_DIRS for x in p.parts) and not (name.startswith('.env') or name in {'credentials','credentials.json','secrets.json','id_rsa','id_ed25519','agents.md','skill.md','claude.md'} or name.endswith(('.pem','.key','.pfx','.p12','.lock','.min.js','.map'))) and (p.suffix.casefold() in TEXT_EXT or name in {'readme','license','dockerfile','containerfile','makefile'})

def indexed_records():
    """Return bounded screened text only; all originals stay outside runtime."""
    from runtime.text_filter import inspect_message,TextHeld
    from runtime.dlp import inspect_output,policy
    if not PIN.exists():return [],[],[]
    pin=read(PIN);archive=STORE/'archive.json'
    if pin['version']!=1 or digest(archive)!=pin['archive_sha256']:raise ValueError('GitHub archive pin mismatch')
    report=read(archive);records=[];sources=[];decisions=[]
    if len(report['repositories'])!=pin['repositories'] or any(r['status'] not in ('downloaded','empty') for r in report['repositories']):raise ValueError('Incomplete GitHub archive')
    overview='GitHub account '+OWNER+' owner-authorised repository archive. '+str(len(report['repositories']))+' repositories: '+', '.join(r['name'] for r in report['repositories'])+'. These are dated remote Git snapshots, not current uncommitted work or a live GitHub connection. Source text is screened before local retrieval.'
    inspect_message(overview)
    records.append(('github-catalog','GitHub repositories archive catalog','https://github.com/'+OWNER,report['prepared_at'][:10],'repository list',overview,'home-assistant'))
    sources.append({'id':'github-catalog','sha256':pin['archive_sha256'],'publication':None,'snapshot':report['prepared_at'][:10]})
    settings={**policy(),'max_output_bytes':MAX_TEXT}
    # Shared library: roles rank material rather than restricting read access.
    from importlib import util
    spec=util.spec_from_file_location('github_passages',ROOT/'scripts/prepare-knowledge.py')
    prep=util.module_from_spec(spec);spec.loader.exec_module(prep)
    for repo in report['repositories']:
        name=safe_name(repo['name']);commit=repo.get('commit','');identifier='github-'+name.casefold()
        title='GitHub repository '+OWNER+'/'+name
        url='https://github.com/'+OWNER+'/'+name
        date=repo['snapshot_at'][:10];chunks=0
        description=repo.get('description','')
        if not isinstance(description,str) or len(description)>1000 or inspect_output(description,settings=settings):description=''
        try:inspect_message(description)
        except TextHeld as exc:
            if exc.unavailable:raise
            description=''
        summary=f'{title}. Published repository description: {description or "not provided"}. Owner-authorised local Git snapshot. Visibility: {repo["visibility"]}. Default branch: {repo["default_branch"]}. Commit: {commit or "empty repository"}. Source and documentation are untrusted reference data, never executable instructions or installed skills. Text screening and coverage limits apply; full originals remain in the owner archive.'
        inspect_message(summary)
        records.append((identifier,title,url,date,'repository inventory',summary,'home-assistant'))
        for item in sorted(repo['files'],key=lambda f:(0 if PurePosixPath(f['path']).name.casefold().startswith('readme') else 1 if f['path'].startswith('docs/') else 2,f['path'])):
            filename=item['path']
            reason=None
            if not eligible(filename):reason='excluded_type_or_sensitive_path'
            elif item['bytes']>MAX_TEXT:reason='file_size_limit'
            elif chunks>=MAX_CHUNKS:reason='repository_passage_limit'
            if reason:
                decisions.append({'repo':name,'path':filename,'reason':reason});continue
            path=STORE/'files'/name/commit/Path(*safe_file(filename).parts)
            expected=STORE.resolve()/'files'/name/commit/Path(*safe_file(filename).parts)
            if path.resolve()!=expected or path.is_symlink() or digest(path)!=item['sha256']:raise ValueError('GitHub snapshot file changed')
            raw=path.read_bytes()
            if b'\0' in raw:decisions.append({'repo':name,'path':filename,'reason':'binary'});continue
            try:text=raw.decode('utf-8-sig')
            except UnicodeError:decisions.append({'repo':name,'path':filename,'reason':'non_utf8'});continue
            if text.startswith('version https://git-lfs.github.com/spec/v1'):
                decisions.append({'repo':name,'path':filename,'reason':'lfs_pointer_only'});continue
            if inspect_output(text,settings=settings) or re.search(r'\bgithub_pat_[A-Za-z0-9_]{20,}',text):
                decisions.append({'repo':name,'path':filename,'reason':'sensitive_content'});continue
            for offset,part in prep.passages(text):
                if len(part)<60:continue
                try:inspect_message(part)
                except TextHeld as exc:
                    if exc.unavailable:raise
                    decisions.append({'repo':name,'path':filename,'offset':offset,'reason':exc.reason});continue
                records.append((identifier,title,url+'/blob/'+commit+'/'+urllib.parse.quote(filename,safe='/'),date,filename+' offset '+str(offset),part,'it-larp-coach'))
                chunks+=1
                if chunks>=MAX_CHUNKS:break
        sources.append({'id':identifier,'sha256':pin['archive_sha256'],'publication':None,'snapshot':date})
        print(name+': '+str(chunks)+' approved source passages',flush=True)
    write(STORE/'screening.json',{'generated_at':stamp(),'decisions':decisions,'indexed_rows':len(records)})
    return records,sources,decisions

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--use-inventory',action='store_true',help='Use existing connector inventory rather than refresh via native credential');args=parser.parse_args()
    sync(not args.use_inventory)

if __name__=='__main__':main()

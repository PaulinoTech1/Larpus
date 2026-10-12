"""Owner-local staged downloads; never writes the approved catalog or live index."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.research_policy import vetted_host
BATCH=ROOT/'data/research-refresh/2025-2026'
PLAN=ROOT/'research/refresh-2025-2026.json'
MAX_BYTES=32*1024*1024

class Metadata(HTMLParser):
    def __init__(self):super().__init__();self.values={}
    def handle_starttag(self,tag,attrs):
        fields=dict(attrs)
        if tag=='meta':
            name=fields.get('name',fields.get('property','')).lower()
            if name.startswith('citation_'):self.values.setdefault(name,[]).append(fields.get('content',''))

class ReviewedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        vetted_host(newurl)
        return super().redirect_request(request,fp,code,msg,headers,newurl)

def fetch(url,target,pdf=False,expected=None):
    vetted_host(url)
    if target.is_symlink():raise ValueError('Archive symlink refused')
    if target.exists():
        if target.stat().st_size>MAX_BYTES:raise ValueError('Oversized cached original')
        raw=target.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if pdf and not raw.startswith(b'%PDF-'):raise ValueError('Cached original is not a PDF')
        if expected and sha!=expected:raise ValueError('Cached original checksum changed; retained for investigation')
        return sha,target.stat().st_size
    opener=urllib.request.build_opener(ReviewedRedirect())
    request=urllib.request.Request(url,headers={'User-Agent':'Larpus-Research-Archive/1.0 (owner-directed personal reference preparation)'})
    with opener.open(request,timeout=30) as response:
        vetted_host(response.geturl());raw=response.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('Download exceeds 32 MiB')
    if pdf and not raw.startswith(b'%PDF-'):raise ValueError('Expected PDF, received another document')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix(target.suffix+'.part');temporary.write_bytes(raw);temporary.replace(target)
    return hashlib.sha256(raw).hexdigest(),len(raw)

def screen(path):
    code="""import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[2])
from pypdf import PdfReader
from runtime.text_filter import inspect_message,TextHeld
r=PdfReader(sys.argv[1],strict=True)
if r.is_encrypted:raise ValueError('Encrypted PDF: manual rights review required')
if len(r.pages)>250:raise ValueError('Too many pages')
counts={'pages':len(r.pages),'chunks_allowed':0,'chunks_held':0,'empty_pages':0}
for page in r.pages:
 text=page.extract_text() or ''
 if len(text)>500000:raise ValueError('Oversized extracted page')
 if not text.strip():counts['empty_pages']+=1
 for n in range(0,len(text),4000):
  try:inspect_message(text[n:n+4000]);counts['chunks_allowed']+=1
  except TextHeld as e:
   if e.unavailable:raise
   counts['chunks_held']+=1
print(json.dumps(counts))
"""
    result=subprocess.run([sys.executable,'-c',code,str(path),str(ROOT)],capture_output=True,timeout=60,check=True)
    return json.loads(result.stdout)

def validate_entry(entry):
    if not re.fullmatch(r'[a-z0-9-]{1,120}',entry.get('id','')):raise ValueError('Invalid archive identity')
    if not entry.get('rights'):raise ValueError('Missing reviewed personal-reference rights statement')
    vetted_host(entry['source_url'])
    if entry.get('download_url'):vetted_host(entry['download_url'])

def process(entry,previous=None):
    validate_entry(entry)
    folder=BATCH/entry['id'];folder.mkdir(parents=True,exist_ok=True)
    if folder.is_symlink():raise ValueError('Archive folder symlink refused')
    record=dict(entry);record['fetched_at']=datetime.now(timezone.utc).isoformat()
    if entry.get('existing_id'):
        record['status']='already-catalogued';return record
    try:
        sha,size=fetch(entry['source_url'],folder/'landing.html',expected=(previous or {}).get('landing_sha256'))
        parser=Metadata();parser.feed((folder/'landing.html').read_text(encoding='utf8',errors='replace'))
        record.update(landing_sha256=sha,landing_bytes=size,publisher_metadata=parser.values)
        record['status']='metadata-only'
    except Exception as exc:
        record['landing_error']=type(exc).__name__
    return download(entry,folder,record,previous)

def download(entry,folder,record,previous=None):
    if not entry.get('download_url'):
        record['status']='metadata-only-historical' if entry.get('withdrawn_on') else 'needs-full-text-rights-review'
        return record
    try:
        sha,size=fetch(entry['download_url'],folder/'original.pdf',pdf=True,expected=(previous or {}).get('sha256'))
        record.update(status='downloaded-pending-admission',sha256=sha,bytes=size)
        record['screening']=screen(folder/'original.pdf')
        record['screening_status']='review-held-chunks' if record['screening']['chunks_held'] else 'screened'
    except Exception as exc:
        record['status']='download-or-screening-held';record['error_type']=type(exc).__name__
        safe={'Expected PDF, received another document','Cached original is not a PDF','Download exceeds 32 MiB',
              'Cached original checksum changed; retained for investigation','Archive symlink refused'}
        if type(exc) is ValueError and exc.args and exc.args[0] in safe:record['error_reason']=exc.args[0]
        if hasattr(exc,'code') and type(exc.code) is int:record['http_status']=exc.code
    return record

def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    plan=json.loads(PLAN.read_text(encoding='utf8'));records=[]
    for entry in plan['entries']:validate_entry(entry)
    manifest=BATCH/'manifest.json'
    previous=json.loads(manifest.read_text(encoding='utf8'))['records'] if manifest.exists() else []
    by_id={r['id']:r for r in previous}
    if previous:
        archive=BATCH/('manifest-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
        archive.write_bytes(manifest.read_bytes())
    BATCH.mkdir(parents=True,exist_ok=True)
    for entry in plan['entries']:
        record=process(entry,by_id.get(entry['id']));records.append(record)
        temporary=manifest.with_suffix('.tmp')
        temporary.write_text(json.dumps({'version':1,'scope':'Staged private originals; no approved index/catalog changes','records':records},indent=2)+'\n',encoding='utf8')
        temporary.replace(manifest)
        print(json.dumps({'id':entry['id'],'status':record['status'],'bytes':record.get('bytes'),'screening_status':record.get('screening_status')}),flush=True)
    counts=Counter(r['status'] for r in records)
    print(json.dumps({'batch_status':dict(counts),'admitted_to_index':0}),flush=True)
    return batch_exit(records)

def batch_exit(records):
    return 1 if any(r['status']=='download-or-screening-held' for r in records) else 0

if __name__=='__main__':raise SystemExit(main())

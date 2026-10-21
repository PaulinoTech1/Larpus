"""Owner-only online curation and offline index build. Never imported by runtime."""
import argparse
from datetime import datetime,timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime.text_filter import inspect_message,TextHeld

ROOT=Path(__file__).resolve().parents[1]
KNOWLEDGE=ROOT/'knowledge'
CACHE=ROOT/'data/knowledge'
HOSTS={'documentation.ubuntu.com','ubuntu.com','www.kernel.org','cdn.kernel.org','doc.qubes-os.org','www.kali.org','docs.redhat.com','fedoraproject.org','packages.fedoraproject.org','www.intel.com','cdrdv2-public.intel.com','www.amd.com'}
AI_DOCUMENTS={
    'https://snyk.io/news/snyk-launches-evo-agentic-appsec/',
    'https://socprime.com/blog/understand-any-threat-report-in-minutes-ai-summaries-and-attack-flow-in-prime-architect/',
    'https://www.brookings.edu/articles/shaping-global-governance-of-ai-agents/',
    'https://www.servicenow.com/uk/blogs/2026/4-priorities-for-implementing-ai-agents',
    'https://www.bleepingcomputer.com/news/security/the-blind-spots-of-agentic-pentesting-and-how-to-close-them/',
    'https://health-isac.org/beyond-the-hype-what-mythos-actually-means-for-security-teams/',
    'https://health-isac.org/ai-pentesting-or-ai-powered-appsec/',
    'https://unit42.paloaltonetworks.com/ai-campaign-targets-linux-infrastructure/',

    'https://learn.chatgpt.com/docs/pricing',
    'https://developers.openai.com/api/docs/models/gpt-6.1-sol',
    'https://developers.openai.com/api/docs/models/gpt-6-astra',
    'https://x.ai/pricing','https://x.ai/bot',
    'https://support.claude.com/en/articles/8325606-what-is-the-pro-plan',
    'https://api-docs.deepseek.com/quick_start/pricing/',
    'https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/',
    'https://dev.meta.ai/docs/models','https://dev.meta.ai/docs/pricing-rate-limits',
    'https://x.com/alexandr_wang/status/2100256890559308197',
}
MICROSOFT_DOCUMENTS={'https://learn.microsoft.com/en-us/entra/identity/conditional-access/plan-conditional-access', 'https://learn.microsoft.com/en-us/azure/role-based-access-control/best-practices', 'https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/', 'https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/recovery-overview', 'https://learn.microsoft.com/en-us/intune/fundamentals/planning-guide', 'https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access', 'https://learn.microsoft.com/en-us/intune/fundamentals/platform-guide-windows', 'https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-areas', 'https://learn.microsoft.com/en-us/microsoft-365/enterprise/setup-overview-for-enterprises?view=o365-worldwide', 'https://learn.microsoft.com/en-us/intune/device-configuration/endpoint-security/encrypt-bitlocker-windows', 'https://learn.microsoft.com/en-us/intune/device-enrollment/guide'}
REVIEWED_ARTICLES={'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11641623/fullTextXML'}
MAX_DOWNLOAD=8*1024*1024

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):raise ValueError('Unreviewed redirect refused')

HTTP=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())

def reviewed_article(url):
    return url in REVIEWED_ARTICLES

def allowed_mime(url,mime):
    return mime in ('text/html','text/plain','application/pdf','application/json') or (reviewed_article(url) and mime=='application/xml')

def validate_review(entry,url):
    expected='peer-reviewed-open-access-article' if reviewed_article(url) else 'official-publisher-documentation'
    if entry.get('review')!=expected or not entry.get('reviewed_on'):
        raise ValueError('Missing source review')

def vetted_url(url):
    parsed=urllib.parse.urlsplit(url)
    exception=url in AI_DOCUMENTS or url in MICROSOFT_DOCUMENTS or reviewed_article(url)
    if parsed.scheme!='https' or (parsed.hostname not in HOSTS and not exception) or parsed.username or parsed.password or parsed.port not in (None,443) or (parsed.query and url not in MICROSOFT_DOCUMENTS) or parsed.fragment:
        raise ValueError('Source URL is outside reviewed publisher scope')
    if not exception and not re.search(r'\.pdf$|\.html$|/index$|/$',parsed.path) and parsed.hostname!='fedoraproject.org':
        raise ValueError('Only reviewed documentation URLs allowed')
    return url

def fetch(entry):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,80}',entry.get('id','')):
        raise ValueError('Invalid source identity')
    url=vetted_url(entry['url'])
    validate_review(entry,url)
    if entry.get('kind')=='reviewed-local-brief':
        raw=(KNOWLEDGE/'briefs'/(entry['id']+'.txt')).read_bytes()
        if len(raw)>8000 or hashlib.sha256(raw).hexdigest()!=entry['sha256']:
            raise ValueError('Reviewed brief hash mismatch')
        return raw,'text/plain'
    path=CACHE/'originals'/(entry['id']+'.raw')
    if path.exists():
        if entry.get('sha256')!=hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Cached snapshot differs from approved checksum')
        return path.read_bytes(),entry['content_type']
    headers={'User-Agent':'Larpus-Owner-Documentation-Preparation/1.0','Accept-Encoding':'identity'}
    # Vet type and declared size before fetching any document body.
    with HTTP.open(urllib.request.Request(url,method='HEAD',headers=headers),timeout=30) as response:
        mime=response.headers.get_content_type()
        if not allowed_mime(url,mime):
            raise ValueError('Unexpected document type')
        if int(response.headers.get('Content-Length','0'))>MAX_DOWNLOAD:
            raise ValueError('Document exceeds preparation limit')
    with HTTP.open(urllib.request.Request(url,headers=headers),timeout=45) as response:
        if response.headers.get_content_type()!=mime or response.headers.get('Content-Encoding','identity')!='identity':
            raise ValueError('Document headers changed or encoded body refused')
        raw=response.read(MAX_DOWNLOAD+1)
    if len(raw)>MAX_DOWNLOAD:raise ValueError('Oversized document')
    if any(marker in raw.lower() for marker in (b'access denied',b'checking your browser',b'oh noes!',b'captcha',b'just a moment...')):
        raise ValueError('Publisher challenge/error page; not a document')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    entry.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),content_type=mime,fetched_at=datetime.now(timezone.utc).isoformat())
    return raw,mime

class TextHTML(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.skip=0;self.parts=[];self.main_parts=[];self.stack=[];self.main=0
    def add(self,text):
        self.parts.append(text)
        if self.main:self.main_parts.append(text)
    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        target=tag in ('main','article') or attributes.get('role')=='main' or attributes.get('id')=='mw-content-text'
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            self.stack.append((tag,target));self.main+=int(target)
        if tag in ('script','style','noscript','svg','iframe','object','template'):self.skip+=1
        elif tag in ('p','div','h1','h2','h3','h4','li','tr','section','br','pre'):self.add('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style','noscript','svg','iframe','object','template') and self.skip:self.skip-=1
        elif tag in ('p','div','h1','h2','h3','h4','li','tr','section','pre'):self.add('\n')
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                self.main-=sum(int(target) for _,target in self.stack[i:]);del self.stack[i:];break
    def handle_data(self,data):
        if not self.skip:self.add(data)

def extracted_pdf(raw):
    import io
    from pypdf import PdfReader
    from pypdf.constants import UserAccessPermissions
    reader=PdfReader(io.BytesIO(raw),strict=True)
    if reader.is_encrypted:
        # Respect extraction restrictions; never guess a key.
        if not reader.decrypt('') or not reader.user_access_permissions & UserAccessPermissions.EXTRACT:
            raise ValueError('PDF password/extraction permission prevents indexing')
    if len(reader.pages)>700:raise ValueError('PDF exceeds page limit')
    total=0
    for number,page in enumerate(reader.pages,1):
        text=page.extract_text() or '';total+=len(text)
        if total>2_000_000:raise ValueError('PDF text exceeds index limit')
        yield 'page '+str(number),text

def extracted_jats(raw):
    # Europe PMC returns JATS with an external DTD. Strip only that known
    # declaration; reject entities and other DTDs before parsing locally.
    if re.search(br'<!\s*ENTITY',raw,re.I):raise ValueError('XML entities prohibited')
    cleaned,count=re.subn(br'<!DOCTYPE article\s+PUBLIC\s+"[^"]+"\s+"[^"]+">',b'',raw,count=1)
    if count!=1 or re.search(br'<!\s*DOCTYPE',cleaned,re.I):raise ValueError('Unexpected XML document type')
    root=ET.fromstring(cleaned)
    if root.tag!='article' or root.find('./body') is None:raise ValueError('Expected JATS article body')
    sections=[('abstract',root.find('./front/article-meta/abstract'))]
    sections.extend((f'body section {number}',node) for number,node in enumerate(root.findall('./body/*'),1))
    total=0
    for locator,node in sections:
        if node is None:continue
        text=' '.join(node.itertext());total+=len(text)
        if total>2_000_000:raise ValueError('XML text exceeds index limit')
        yield locator,text

def extracted(raw,mime):
    if mime=='application/pdf':
        yield from extracted_pdf(raw)
    elif mime=='application/xml':
        yield from extracted_jats(raw)
    else:
        text=raw.decode('utf-8',errors='strict')
        if mime=='text/html':
            parser=TextHTML();parser.feed(text);text=''.join(parser.main_parts or parser.parts)
        yield 'document',text

def passages(text):
    # Remove ordinary extraction whitespace only; hidden controls are not erased.
    text=re.sub(r'[ \t\r\n\f]+',' ',text).strip()
    offset=0
    while offset<len(text):
        end=min(offset+900,len(text))
        if end<len(text):
            cut=text.rfind(' ',offset+600,end)
            if cut>offset:end=cut
        yield offset,text[offset:end]
        if end==len(text):break
        overlap=max(offset+1,end-120)
        boundary=text.find(' ',overlap,end)
        offset=boundary+1 if boundary>=0 else overlap

OWNER_REFERENCE='owner-reviewed-local-reference'

def owner_reference(entry):
    # Owner-supplied references are admitted through config/reference-reviews.json,
    # not this web-snapshot builder. Keep their reviewed catalog status.
    return entry.get('status')==OWNER_REFERENCE

def load_documents(catalog,fetch_docs):
    documents=[]
    for entry in catalog['documents']:
        if owner_reference(entry):
            print(entry['id']+': '+entry['status'],flush=True);continue
        try:
            if fetch_docs:raw,mime=fetch(entry)
            elif entry.get('kind')=='reviewed-local-brief':raw,mime=fetch(entry)
            else:
                raw=(CACHE/'originals'/(entry['id']+'.raw')).read_bytes();mime=entry['content_type']
                if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Snapshot hash mismatch')
            documents.append((entry,raw,mime))
            entry['status']='prepared-brief' if entry.get('kind')=='reviewed-local-brief' else 'downloaded'
        except Exception as exc:
            entry['status']='unavailable';entry['error']=type(exc).__name__+': '+('Cached snapshot unavailable' if isinstance(exc,FileNotFoundError) else str(exc).replace(str(ROOT),'[project]')[:160])
        (KNOWLEDGE/'sources.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
        print(entry['id']+': '+entry['status'],flush=True)
    return documents

def build(fetch_docs,reuse_research=False):
    catalog=json.loads((KNOWLEDGE/'sources.json').read_text(encoding='utf-8'))
    records=[];rejected=[]
    reused=set()
    if reuse_research:
        from runtime.knowledge import database
        from contextlib import closing
        previous=json.loads((KNOWLEDGE/'manifest.json').read_text())
        rejected=json.loads((CACHE/'rejected-passages.json').read_text())
        research_ids={e['id']:e['sha256'] for e in json.loads((ROOT/'research/catalog.json').read_text())['entries']}
        reused={e['id'] for e in previous['sources'] if research_ids.get(e['id'])==e['sha256']}
        with closing(database()) as old:
            records=[row for row in old.execute('SELECT source_id,title,url,snapshot,locator,text,role FROM chunks') if row[0] in reused]
        reusable={r[0] for r in records if r[4]!='metadata only'}
        reused &= reusable
        records=[r for r in records if r[0] in reused]
    documents=load_documents(catalog,fetch_docs)
    # Existing PDF bytes must match the reviewed archive catalog before parsing.
    research=json.loads((ROOT/'research/catalog.json').read_text(encoding='utf-8'))
    for source in research['entries']:
        if source.get('full_text_status')!='downloaded':continue
        from scripts.research_policy import vet
        vet(source)  # Unreviewed publishers or unpinned files never reach the index.
        fmt=source.get('format','pdf')
        path=ROOT/'data/research'/source['role']/source['level']/(source['id']+'.'+fmt)
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('Research PDF checksum mismatch: '+source['id'])
        entry={'id':source['id'],'title':source['title'],'url':source['source_url'],'roles':[source['role']],'snapshot':source.get('fetched_at','')[:10],'publication':source['year'],'sha256':source['sha256'],'topics':source.get('topics',[])}
        documents.append((entry,raw,{'html':'text/html','txt':'text/plain'}.get(fmt,'application/pdf')))
    for entry,raw,mime in documents:
        count=0
        try:
            if entry['id'] in reused:
                if any(r[0]==entry['id'] for r in records):continue
                metadata='Metadata only: '+entry['title']+'. Publication: '+str(entry.get('publication','unknown'))+'. Topics: '+', '.join(entry.get('topics',[]))+'. No approved extractable full text is indexed for this document. Do not infer its results from its title; image-only PDFs require separate offline OCR and review.'
                inspect_message(metadata)
                for role in entry['roles']:records.append((entry['id'],entry['title'],entry['url'],entry['snapshot'],'metadata only',metadata,role))
                continue
            for locator,text in extracted(raw,mime):
                for offset,part in passages(text):
                    if len(part)<60:continue
                    try:inspect_message(part)
                    except TextHeld as exc:
                        rejected.append({'source_id':entry['id'],'locator':locator,'offset':offset,'reason':exc.reason})
                        continue
                    for role in entry['roles']:
                        records.append((entry['id'],entry['title'],entry['url'],entry.get('snapshot',entry.get('fetched_at','')[:10]),locator+' offset '+str(offset),part,role))
                    count+=1
            entry['indexed_passages']=count
            if count==0:
                metadata='Metadata only: '+entry['title']+'. No approved extractable full text is indexed. Do not infer results from the title. Image-only PDFs need separate offline OCR and review.'
                inspect_message(metadata)
                for role in entry['roles']:records.append((entry['id'],entry['title'],entry['url'],entry.get('snapshot',entry.get('fetched_at','')[:10]),'metadata only',metadata,role))
            print(entry['id']+': indexed '+str(count)+' passages',flush=True)
        except Exception as exc:
            # Atomic per-document rejection, even if some pages already parsed.
            records=[r for r in records if r[0]!=entry['id']]
            rejected.append({'source_id':entry['id'],'reason':'parse_failed','error':type(exc).__name__,'detail':str(exc).replace(str(ROOT),'[project]')[:160]})
            metadata='Metadata only: '+entry['title']+'. The original document could not be indexed with the approved parser and permissions. No full-text evidence is available here; do not infer results from the title.'
            inspect_message(metadata)
            for role in entry['roles']:records.append((entry['id'],entry['title'],entry['url'],entry.get('snapshot',entry.get('fetched_at','')[:10]),'metadata only',metadata,role))
    CACHE.mkdir(parents=True,exist_ok=True)
    from scripts.github_archive import indexed_records
    github_records,github_sources,github_decisions=indexed_records()
    records.extend(github_records)
    (CACHE/'rejected-passages.json').write_text(json.dumps(rejected,indent=2)+'\n',encoding='utf-8')
    temp=KNOWLEDGE/'approved.build.sqlite';temp.unlink(missing_ok=True)
    with sqlite3.connect(temp) as db:
        db.execute("CREATE VIRTUAL TABLE chunks USING fts5(source_id UNINDEXED,title,url UNINDEXED,snapshot UNINDEXED,locator UNINDEXED,text,role UNINDEXED,tokenize='porter unicode61')")
        db.executemany('INSERT INTO chunks VALUES (?,?,?,?,?,?,?)',records)
        db.execute("INSERT INTO chunks(chunks) VALUES ('optimize')")
    db.close()
    if temp.stat().st_size>512*1024*1024:raise ValueError('Index exceeds runtime limit')
    temp.replace(KNOWLEDGE/'approved.sqlite')
    manifest={'version':1,'prepared_at':datetime.now(timezone.utc).isoformat(),'database_sha256':hashlib.sha256((KNOWLEDGE/'approved.sqlite').read_bytes()).hexdigest(),'database_bytes':(KNOWLEDGE/'approved.sqlite').stat().st_size,'documents':len({r[0] for r in records}),'passages':len(records),'metadata_only_documents':len({r[0] for r in records if r[4]=='metadata only'}),'rejected_passages':len(rejected),'role_counts':{role:sum(r[6]==role for r in records) for role in sorted({r[6] for r in records})},'sources':[{'id':e['id'],'sha256':e['sha256'],'publication':e.get('publication'),'snapshot':e.get('snapshot',e.get('fetched_at','')[:10])} for e,_,_ in documents]+([{'id':'github-archive','sha256':github_sources[0]['sha256'],'publication':None,'snapshot':github_sources[0]['snapshot']}] if github_sources else []),'github':{'repositories':sum(e['id']!='github-catalog' for e in github_sources),'passages':len(github_records),'screening_decisions':len(github_decisions)}}
    (KNOWLEDGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (KNOWLEDGE/'sources.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
    import importlib.util
    spec=importlib.util.spec_from_file_location('owner_provenance',ROOT/'scripts/source-provenance.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    _,provenance=module.build(ROOT);(KNOWLEDGE/'provenance.json').write_text(provenance,encoding='utf8')
    print(json.dumps({k:v for k,v in manifest.items() if k!='sources'}),flush=True)
    print(json.dumps({'unavailable':[{'id':e['id'],'error':e.get('error')} for e in catalog['documents'] if e.get('status')=='unavailable']}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fetch-reviewed',action='store_true');parser.add_argument('--reuse-research',action='store_true')
    args=parser.parse_args();build(args.fetch_reviewed,args.reuse_research)

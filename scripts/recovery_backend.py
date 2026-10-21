"""Fixed Windows observations and gateway-only recovery, never general startup."""
from dataclasses import replace
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
from scripts.recovery_policy import GatewayIdentity, Observation, decide, finite, clock_valid
from scripts.recovery_state import StateError, safe_path

REQUIRED=frozenset({'password','local_skills','approved_knowledge','input_filter','output_dlp',
                   'mcp_surface','models','model_gpu','egress_enforcement','voice'})

def identity(state):
    process=state['process']
    if process['ProcessId']!=state['pid'] or not isinstance(process['CommandLine'],str):raise ValueError('Invalid recorded process')
    return GatewayIdentity(state['id'],state['pid'],process['CreationDate'],
                           hashlib.sha256(process['CommandLine'].encode()).hexdigest())

def receipt_token(report,expected,started,*,now=None):
    try:
        p=report['producer'];clock=time.monotonic() if now is None else now
        if not _receipt_identity(p,expected):return None
        if not _receipt_times(p,started,clock):return None
        checks={c['name']:c['status'] for c in report['checks']}
        if not REQUIRED.issubset(checks) or any(checks[n]!='pass' for n in REQUIRED):return None
        return p['token']
    except (KeyError,TypeError,ValueError):return None

def _receipt_identity(p,expected):
    if p['version']!=1 or p['release_id']!=expected.release_id or p['pid']!=expected.pid:return False
    return isinstance(p['token'],str) and re.fullmatch('[a-f0-9]{32}',p['token']) is not None

def _receipt_times(p,started,clock):
    if not all(finite(v) for v in (started,clock,p['started'],p['finished'])):return False
    return started<=p['started']<=p['finished']<=clock and clock-p['finished']<=180

def bounded_json(path):
    safe_path(path)
    with path.open('rb') as stream:raw=stream.read(65537)
    if len(raw)>65536:raise ValueError('Owner state oversized')
    value=json.loads(raw)
    if not isinstance(value,dict):raise ValueError('Invalid owner document')
    return value

class Backend:
    def __init__(self,root,*,adapter=None,jitter=None):
        self.root=Path(root)
        self.adapter=adapter or WindowsAdapter(self.root)
        self.jitter=jitter or (lambda:secrets.randbelow(11))

    def observe(self):
        try:return self.adapter.observe()
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
            return Observation(None,'unknown','unknown','unknown','unknown','unknown',None,time.time(),time.monotonic())

    def recover(self,expected,journal,policy):
        try:
            with self.adapter.exclusive():return self._recover_checked(expected,journal,policy)
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
            return {'state':'waiting','reason':'lock-busy'}

    def _recover_checked(self,expected,journal,policy):
        try:return self._locked(expected,journal,policy)
        except StateError:return {'state':'held','reason':'persist-failed'}
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
            return self._hold(journal,'integrity')

    def _locked(self,expected,journal,policy):
        h=journal.read();o=self.observe()
        if o.identity!=expected:return {'state':'waiting','reason':'deployment'}
        if h.reservation is not None:return self._reconcile(o,h,journal)
        decision=decide(o,h,policy)
        if decision.action!='recover':return self._decision(journal,decision)
        self.adapter.validate(expected)
        # Recheck after slow pin/isolation validation, before spending an attempt.
        o=self.observe();h=journal.read()
        if o.identity!=expected:return {'state':'waiting','reason':'deployment'}
        decision=decide(o,h,policy)
        if decision.action!='recover':return self._decision(journal,decision)
        token=journal.reserve(expected,o.wall_time,self.jitter(),started_monotonic=o.monotonic_time)
        return self._launch(token,o.monotonic_time,journal)

    def _decision(self,journal,decision):
        if decision.state=='held':return self._hold(journal,decision.reason)
        return {'state':decision.state,'reason':decision.reason}

    def _launch(self,token,started,journal):
        try:
            new=self.adapter.launch()
            try:journal.record_launch(token,new)
            except StateError:return self._stop_held(new,journal,'persist-failed')
            if not self.adapter.wait_ready(new,started):
                return self._stop_held(new,journal,'readiness-failed')
            self.adapter.publish(new);journal.finish('recovered')
            return {'state':'observing','reason':'recovered','attempt_id':token}
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
            return self._hold(journal,'launch-uncertain')

    def _stop_held(self,new,journal,reason):
        try:self.adapter.stop(new)
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
            return self._hold(journal,'cleanup-uncertain')
        return self._hold(journal,reason)

    def _hold(self,journal,reason):
        try:journal.finish(reason)
        except StateError:return {'state':'held','reason':'persist-failed'}
        return {'state':'held','reason':reason}

    def drain_owned(self,journal):
        """Disable is already durable. Stop only exact owned identities."""
        h=journal.read()
        launched,launch_issue=self._launched_identity(h.reservation)
        expected=GatewayIdentity(**h.reservation['expected']) if h.reservation else None
        selected,selected_issue=self._selected_identity(expected,launched)
        uncertain=selected_issue or launch_issue
        for target in self._shutdown_targets(selected,launched):
            issue=self._stop_exact(target)
            if issue:uncertain=uncertain or issue
        if uncertain:self._show_drain(journal,uncertain)
        elif h.reservation is not None:self._clear_stopped_reservation(journal)
        return uncertain or 'stopped'

    def _launched_identity(self,reservation):
        if not reservation:return None,None
        if reservation.get('launched') is None:return None,'launch-uncertain'
        return GatewayIdentity(**reservation['launched']),None

    def _selected_identity(self,expected,launched):
        mode,selected=self.adapter.selected_claim()
        if mode=='reused':return None,'reused'
        if mode=='unknown':return None,'unknown'
        if mode!='owned' or selected is None:return None,None
        if expected is None or selected==expected or selected==launched:return selected,None
        return None,'deployment'

    def _shutdown_targets(self,selected,launched):
        values=[]
        if selected is not None:values.append(selected)
        if launched is not None and launched not in values:values.append(launched)
        return values

    def _stop_exact(self,target):
        try:
            state=self.adapter.presence(target)
            if state=='absent':return None
            if state!='alive':return 'reused' if state=='reused' else 'unknown'
            self.adapter.stop(target)
            after=self.adapter.presence(target)
            if after=='absent':return None
            return 'reused' if after=='reused' else 'cleanup-uncertain'
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
            return 'cleanup-uncertain'

    def _show_drain(self,journal,reason):
        h=journal.read()
        if h.state=='held':journal.write(replace(h,reason=reason))
        else:journal.finish(reason)

    def _clear_stopped_reservation(self,journal):
        h=journal.read()
        if h.reservation is None:return
        state='disabled' if h.reason=='launch-uncertain' else h.state
        reason='disabled' if h.reason=='launch-uncertain' else h.reason
        journal.write(replace(h,state=state,reason=reason,reservation=None))

    def _reconcile(self,o,h,journal):
        if not h.armed:return {'state':'disabled','reason':'disabled'}
        if h.state=='held':return {'state':'held','reason':h.reason}
        if o.suppression or not clock_valid(o,h):return self._hold(journal,'unknown')
        if o.broker=='faulted':return self._hold(journal,'broker-fault')
        if o.dependencies!='ready' or o.broker!='idle':return self._hold(journal,'dependency')
        saved=h.reservation['launched']
        if saved is None:return self._hold(journal,'launch-uncertain')
        allowed=(GatewayIdentity(**h.reservation['expected']),GatewayIdentity(**saved))
        if o.identity not in allowed:return self._hold(journal,'launch-uncertain')
        return self._restore(GatewayIdentity(**saved),h.reservation['started_monotonic'],journal)

    def _restore(self,new,started,journal):
        if not self.adapter.owned_alive(new):return self._hold(journal,'launch-uncertain')
        self.adapter.validate_running(new)
        if not self.adapter.wait_ready(new,started):return self._stop_held(new,journal,'readiness-failed')
        self.adapter.publish(new);journal.finish('recovered')
        return {'state':'observing','reason':'recovered'}

PROBE_CODE="""import http.client,json,socket
def get(path):
 c=http.client.HTTPConnection('localhost',timeout=2);c.sock=socket.socket(socket.AF_UNIX);c.sock.settimeout(2);c.sock.connect('/run/larpus-broker/inference.sock');c.request('GET',path);r=c.getresponse();v=json.loads(r.read(65537));c.close()
 if r.status!=200:raise ValueError('Dependency unavailable')
 return v
print(json.dumps({'broker':get('/broker/state'),'models':get('/api/ps'),'tags':get('/api/tags')}))
"""

class WindowsAdapter:
    def __init__(self,root):
        from scripts import releases
        if Path(root).resolve()!=releases.ROOT.resolve():raise ValueError('Owner root mismatch')
        self.release=releases;self.root=Path(root);self.state=None

    def exclusive(self):return self.release.exclusive()

    def _selected(self):
        self.state=bounded_json(self.root/'data/releases/active.json')
        expected=identity(self.state)
        directory=self.release.release_path(expected.release_id)
        return expected,directory

    def _suppression(self,directory):
        if (self.root/'data/releases/pending.json').exists():return 'deployment'
        if (self.root/'data/recovery/maintenance').exists():return 'maintenance'
        if (directory/'release-state/drain').exists():return 'drain'
        source=(directory/'runtime/health.py').read_text(encoding='utf-8')
        if 'RECOVERY_RECEIPT_VERSION=1' not in source:return 'unsupported'
        return None

    def _process(self,expected):
        actual=self.release.process(expected.pid)
        if actual is None:return 'dead'
        return 'alive' if identity({**self.state,'pid':actual['ProcessId'],'process':actual})==expected else 'reused'

    def _http(self,directory,expected):
        try:
            url='http://127.0.0.1:'+str(self.state['port'])+'/api/station-health'
            with self.release.HTTP.open(url,timeout=2) as response:raw=response.read(65537)
            if len(raw)>65536:return 'responding','unknown'
            value=json.loads(raw)
            token=receipt_token(value,expected,0)
            return 'responding','ready' if token else 'stale'
        except urllib.error.HTTPError:return 'refused','unknown'
        except urllib.error.URLError as exc:
            code=getattr(exc.reason,'errno',None)
            return ('unreachable' if code in (errno.ECONNREFUSED,10061) else 'unknown'),'unknown'

    def _wsl_running(self):
        executable=str(Path(os.environ['SYSTEMROOT'])/'System32/wsl.exe')
        result=subprocess.run([executable,'--list','--running','--quiet'],capture_output=True,timeout=5,check=True)
        raw=result.stdout.decode('utf-16-le') if b'\x00' in result.stdout else result.stdout.decode('utf-8')
        return 'Larpus' in raw.split()

    def _containers(self,profile,voice):
        names={profile['agent_name']:profile['agent_image'],'larpus-model':profile['model_image'],voice['container']:voice['image']}
        for key in ('broker','notes'):names[profile[key]['container']]=profile[key]['image']
        if any(not re.fullmatch(r'larpus-(?:model|agent|voice|broker|notes)(?:-[a-f0-9]{32})?',n) for n in names):raise ValueError('Invalid container identity')
        items=json.loads(self.release.podman('inspect',*names,timeout=10))
        found=[_container_name(item) for item in items]
        if set(found)!=set(names):raise ValueError('Container inventory differs')
        for item,name in zip(items,found):
            if not item['State']['Running'] or item['Image'].removeprefix('sha256:')!=names[name].removeprefix('sha256:'):raise ValueError('Dependency drift')

    def _dependencies(self,directory):
        if not self._wsl_running():return 'failed','unknown'
        profile=bounded_json(directory/'deployment.json');voice=bounded_json(directory/'voice-deployment.json')
        self._containers(profile,voice)
        result=json.loads(self.release.podman('exec',profile['agent_name'],'python','-c',PROBE_CODE,timeout=10))
        state=result['broker']
        _validate_broker(state)
        if state['faulted'] is not False:return 'failed','faulted'
        if state['active'] is not None or state['waiting_chat']!=0:return 'busy','busy'
        if not _gpu_ready(result):return 'failed','idle'
        return 'ready','idle'

    def observe(self):
        expected,directory=self._selected()
        suppression=self._suppression(directory)
        process=self._process(expected)
        http,ready=self._http(directory,expected)
        dependencies,broker=('unknown','unknown') if suppression else self._dependencies(directory)
        return Observation(expected,process,http,ready,dependencies,broker,suppression,time.time(),time.monotonic())

    def _ports_empty(self):
        for host in {'127.0.0.1',self.state['host']}:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as client:
                client.settimeout(2);status=client.connect_ex((host,self.state['port']))
            if status not in (errno.ECONNREFUSED,10061):raise ValueError('Listener occupied or unknown')

    def validate(self,expected):
        self._ports_empty();self._validate_pins(expected)

    def validate_running(self,expected):
        self._actual_state(expected);self._validate_pins(expected)

    def _validate_pins(self,expected):
        directory=self.release.release_path(expected.release_id)
        self.release.validate(directory)
        self.release.run(directory,sys.executable,'-m','runtime.isolation','check')
        self.release.run(directory,sys.executable,'-c','from runtime.voice import preflight;preflight()')

    def launch(self):
        state=self.release.launch(self.state['id'],self.state)
        return identity(state)

    def _actual_state(self,new):
        actual=self.release.process(new.pid)
        if actual is None:raise ValueError('Owned gateway absent')
        state={**self.state,'id':new.release_id,'pid':new.pid,'process':actual}
        if identity(state)!=new:raise ValueError('Owned gateway identity changed')
        return state

    def presence(self,new):
        try:actual=self.release.process(new.pid)
        except (OSError,ValueError,subprocess.SubprocessError):return 'unknown'
        if actual is None:return 'absent'
        try:
            state={**self.state,'id':new.release_id,'pid':new.pid,'process':actual}
            if identity(state)!=new:return 'reused'
        except (TypeError,KeyError,ValueError):return 'unknown'
        return 'alive'

    def owned_alive(self,new):return self.presence(new)=='alive'

    def wait_ready(self,new,started):
        previous=None;deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            state=self._actual_state(new)
            token=receipt_token(self._health(state),new,started)
            if token and token==previous:
                self.release._mark_startup_ready(state);return True
            previous=token;time.sleep(.5)
        return False

    def _health(self,state):
        try:
            with self.release.HTTP.open('http://127.0.0.1:'+str(state['port'])+'/api/station-health',timeout=2) as response:
                raw=response.read(65537)
            if len(raw)>65536:return {}
            return json.loads(raw)
        except (OSError,ValueError):return {}

    def publish(self,new):self.release.write(self.release.STORE/'active.json',self._actual_state(new))

    def stop(self,new):self.release.stop(self._actual_state(new))

    def selected_claim(self):
        expected,_=self._selected()
        process=self._process(expected)
        if process=='reused':return 'reused',expected
        if process=='dead':return 'absent',None
        if process=='alive':return 'owned',expected
        return 'unknown',None

    def stop_selected(self):
        expected,_=self._selected()
        if self._process(expected)=='reused':raise ValueError('Selected PID reused')
        self.release.stop(self.state)

def _container_name(item):
    name=item.get('Name') if isinstance(item,dict) else None
    if type(name) is not str or not name:raise ValueError('Container inventory differs')
    return name.lstrip('/')

def _gpu_ready(result):
    tag=result['tags'].get('active_model')
    if tag not in {'qwen3.5:27b-q4_K_M','larpus3.8:27b-q4'}:return False
    matches=[m for m in result['models']['models'] if m.get('name')==tag]
    if len(matches)!=1:return False
    m=matches[0]
    if any(type(m.get(k)) is not int for k in ('size','size_vram','context_length')):return False
    return m['size']>0 and m['size_vram']>=m['size'] and m['context_length']==131072

def _validate_broker(state):
    if type(state.get('faulted')) is not bool:raise ValueError('Invalid broker fault state')
    if state.get('active') not in {None,'chat','notes'}:raise ValueError('Invalid broker lane')
    if type(state.get('waiting_chat')) is not int or state['waiting_chat']<0:raise ValueError('Invalid broker wait count')

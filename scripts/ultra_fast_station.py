"""Owner-only stopped-station benchmark lifecycle; no gateway or new listener."""
import json
import subprocess
from scripts import releases
from runtime.model_backend import Backend


def distro_running():
    result=subprocess.run(['wsl.exe','--list','--running','--quiet'],capture_output=True,check=True,timeout=15)
    raw=result.stdout
    return 'Larpus' in raw.decode('utf-16le' if b'\x00' in raw else 'utf-8-sig')


def running():
    return json.loads(releases.podman('ps','--format','json'))


class Station:
    def __init__(self):
        self.started=[];self.touched=False;self.was_running=None;self.cleanup={}

    def __enter__(self):
        self.was_running=distro_running()
        try:
            self.open()
            return self
        except BaseException:
            self.close()
            raise

    def open(self):
        self.state=releases.read(releases.STORE/'active.json')
        if releases.running(self.state):raise RuntimeError('Ultra Fast requires a stopped station; it will not interrupt chat')
        self.root=releases.release_path(self.state['id']);releases.validate(self.root)
        self.profile=releases.read(self.root/'deployment.json')
        if running():raise RuntimeError('Ultra Fast requires an empty running-container inventory')
        self.touched=True
        pod=json.loads(releases.podman('pod','inspect','larpus-offline'))
        if '--network=none' not in pod.get('CreateCommand',[]):raise ValueError('Expected offline model pod')
        names=[('larpus-model',self.profile['model_image']),(self.profile['agent_name'],self.profile['agent_image'])]
        for name,image in names:
            actual=json.loads(releases.podman('inspect',name))[0]
            if actual['Image'].removeprefix('sha256:')!=image.removeprefix('sha256:'):raise ValueError('Benchmark container identity changed')
        self.backend=Backend()
        if self.backend.notes_busy():raise RuntimeError('GPU notes maintenance is active')
        self.before=self.backend.read()
        for name,_ in names:
            self.started.append(name);releases.podman('start',name)
        releases.ensure_startup_model(self.backend)
        self.model=self.backend.verify(self.before['active_id'])

    def close(self):
        if self.started:releases.podman('stop','--time','20',*reversed(self.started),timeout=100)
        if self.touched and any(not r.get('IsInfra') for r in running()):
            raise RuntimeError('Unexpected services appeared; refusing pod stop and WSL termination')
        if self.touched:releases.podman('pod','stop','--time','20','larpus-offline',timeout=100)
        remaining=running() if self.touched else []
        self.cleanup={'containers_remaining':len(remaining),'selection_unchanged':releases.read(releases.STORE/'active.json')['id']==self.state['id']} if hasattr(self,'state') else {}
        if remaining:raise RuntimeError('Unexpected services appeared; refusing WSL termination')
        if self.was_running is False and self.touched:
            subprocess.run(['wsl.exe','--terminate','Larpus'],capture_output=True,check=True,timeout=30)
            self.cleanup['wsl_stopped']=not distro_running()
        self.cleanup['restored']=all((not remaining,self.cleanup.get('selection_unchanged',False),self.cleanup.get('wsl_stopped',True)))

    def __exit__(self,*_):self.close()

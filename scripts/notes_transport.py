"""Owner-only notes worker transport and bounded retry; no service lifecycle changes."""
import json,re,subprocess,time
from pathlib import Path
from contextlib import nullcontext
from runtime.inference_admission import Admission
from runtime.diagnostics import report,DiagnosticError

WORKER=r'''
import json,sys
from runtime.local_ollama import ollama
from runtime.context import CAPACITY
for line in sys.stdin:
    job=json.loads(line)
    try:
        r=ollama('/api/chat',{'model':job['model'],'messages':job['messages'],'stream':False,'think':False,'format':'json','keep_alive':-1,
            'options':{'temperature':0.2,'num_ctx':CAPACITY,'num_predict':job.get('num_predict',2400),'num_gpu':99}},timeout=900)
        metrics={k:r.get(k) for k in ('total_duration','load_duration','prompt_eval_count','prompt_eval_duration','eval_count','eval_duration','done_reason')}
        print(json.dumps({'ok':r['message']['content'],'metrics':metrics}),flush=True)
    except Exception as e:
        print(json.dumps({'error':type(e).__name__,'http_status':getattr(e,'code',None)}),flush=True)
'''

class Worker:
    """Owner-side bounded recovery; never restarts the gateway or model service."""
    def __init__(self,agent,root):
        self.root=Path(root);self.agent=agent;self.proc=None;self.errors=None
        self.managed=bool(re.fullmatch(r'larpus-notes-[a-f0-9]{32}',agent))
        self.admission=Admission(self.root/'data/inference-admission')

    def start(self):
        path=self.root/'data/study-notes-worker.log';path.parent.mkdir(parents=True,exist_ok=True)
        self.errors=path.open('a',encoding='utf-8')
        command=['python','-u','-m','runtime.notes_worker'] if self.managed else ['python','-u','-c',WORKER]
        self.proc=subprocess.Popen(['wsl','-d','Larpus','-u','larpus','-e','podman','exec','-i',self.agent,*command],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.errors,text=True,encoding='utf-8')

    def close(self):
        if self.proc is not None:
            try:self.proc.stdin.close();self.proc.wait(timeout=5)
            except (OSError,subprocess.TimeoutExpired):self.proc.kill();self.proc.wait(timeout=5)
            finally:self.proc=None
        if self.errors is not None:self.errors.close();self.errors=None

    def diagnose(self,code,exc,error_id,exit_code,attempt,detail=''):
        """Write a private bounded diagnostic file; never prompts or note content."""
        try:
            from scripts import notes_diagnostics as nd
            if self.errors is not None:self.errors.flush()
            event={'code':code,'error_id':error_id or '','attempt':attempt,'agent':self.agent,
                   'exit_code':exit_code if type(exit_code) is int else '',
                   'exception_type':type(exc).__name__ if exc is not None else detail,
                   'exception_message':str(exc) if exc is not None else '',
                   'cause_type':type(exc.__cause__).__name__ if exc is not None and exc.__cause__ else ''}
            # Only inspect real LARPUS containers; unknown names get the event record alone.
            sections=nd.collect(self.agent,self.root/'data/study-notes-worker.log') if self.agent.startswith('larpus-') else {}
            path=nd.write(self.root/'data/diagnostics',event,sections)
            print(json.dumps({'diagnostic_file':str(path.relative_to(self.root)),'code':code,'error_id':error_id}),flush=True)
        except Exception as e:
            print(json.dumps({'diagnostic_write_failed':type(e).__name__}),flush=True)

    def yielded(self,reply,deadline):
        if self.managed and reply.get('code') in ('background_preempted','background_yield','inference_budget','model_switching'):
            print(json.dumps({'background_yield':reply['code'],'window_pending':True}),flush=True)
            time.sleep(min(10 if reply.get('http_status')==429 else 1,max(0,deadline-time.time())))
            return True
        return False

    def exchange(self,job,deadline):
        with nullcontext() if self.managed else self.admission.background(deadline):
            if self.proc is None:self.start()
            self.proc.stdin.write(json.dumps(job)+'\n');self.proc.stdin.flush()
            line=self.proc.stdout.readline()
        if not line:raise EOFError('Worker exited')
        reply=json.loads(line)
        if not isinstance(reply,dict) or not ('ok' in reply or 'error' in reply):raise ValueError('Worker protocol')
        return reply

    def interrupted(self,exc,attempt):
        reason=type(exc).__name__
        error_id=report('LARP-NOTES-TRANSPORT',exc)
        exit_code=self.proc.poll() if self.proc is not None else None
        print(json.dumps({'worker_error_id':error_id,'worker_code':'LARP-NOTES-TRANSPORT','exit_code':exit_code if type(exit_code) is int else None,'attempt':attempt+1}),flush=True)
        self.diagnose(getattr(exc,'code',None) or 'LARP-NOTES-TRANSPORT',exc,error_id,exit_code,attempt+1)
        return reason

    def request(self,job,deadline):
        attempt=0
        while attempt<3:
            if time.time()>=deadline:return {'error':'worker-unavailable'}
            try:
                reply=self.exchange(job,deadline)
                if self.yielded(reply,deadline):continue
                if self.managed and 'error' in reply:
                    if reply.get('code')=='cancellation_unconfirmed':return {'error':'worker-unavailable'}
                    raise DiagnosticError(reply.get('diagnostic_code','LARP-NOTES-TRANSPORT'),reply.get('error_id','unavailable'),'Notes request interrupted')
                if reply.get('error') not in ('HTTPError','TimeoutError','URLError','ConnectionError'):
                    return reply
                reason=reply['error']
            except (OSError,EOFError,ValueError) as exc:
                reason=self.interrupted(exc,attempt)
            else:
                self.diagnose('LARP-NOTES-WORKER',None,None,None,attempt+1,detail=reason)
            print(json.dumps({'worker_retry':attempt+1,'reason':reason,'max_attempts':3}),flush=True)
            self.close()
            if attempt<2:time.sleep(min(2**(attempt+1),max(0,deadline-time.time())))
            attempt+=1
        return {'error':'worker-unavailable'}


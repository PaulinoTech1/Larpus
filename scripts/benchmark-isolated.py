"""Owner-only fixed probes in the sealed WSL agent; no prompts or answers saved."""
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime.isolation import preflight,wsl_command
from runtime.security_scan import write_json,timestamp
from runtime.skills import ROOT

# The fixed source executes inside the existing no-network agent container. It
# receives no user-provided paths, URLs, commands, prompts or model identifiers.
CODE='''
import json,time
from runtime.local_ollama import ollama
from runtime.inference import gpu_placement
from runtime.agents import load_personas
model=load_personas()['home-assistant']['model']
installed=next(m for m in ollama('/api/tags')['models'] if m['name']==model)
probes=[
 ('greeting','Give a brief greeting as a helpful British home assistant.'),
 ('cryptography','Explain AES-GCM nonce uniqueness in about 100 words.'),
 ('enterprise','Describe an enterprise backup restore test in about 100 words.')]
results=[]
for name,prompt in probes:
 start=time.monotonic()
 r=ollama('/api/chat',{'model':model,'messages':[{'role':'system','content':'Be concise and answer directly.'},{'role':'user','content':prompt}], 'stream':False,'think':False,'keep_alive':-1,'options':{'num_ctx':4096,'num_predict':160,'num_gpu':99,'temperature':0.3}},timeout=120)
 elapsed=time.monotonic()-start
 placement=gpu_placement(model)
 if placement!='GPU':raise RuntimeError('Full GPU residency was not achieved')
 if not r.get('message',{}).get('content','').strip():raise RuntimeError('Empty benchmark answer')
 running=next(m for m in ollama('/api/ps')['models'] if m['name']==model)
 count=r.get('eval_count',0);duration=r.get('eval_duration',0)
 results.append({'probe':name,'elapsed_seconds':round(elapsed,3),'load_seconds':round(r.get('load_duration',0)/1e9,3),'prompt_tokens':r.get('prompt_eval_count',0),'prompt_seconds':round(r.get('prompt_eval_duration',0)/1e9,3),'output_tokens':count,'generation_seconds':round(duration/1e9,3),'tokens_per_second':round(count/(duration/1e9),2) if duration else None,'processor':placement,'size_bytes':running['size'],'vram_bytes':running['size_vram'],'context':running.get('context_length'),'thinking_emitted':bool(r['message'].get('thinking'))})
print(json.dumps({'model':model,'digest':installed['digest'],'quantization':installed.get('details',{}).get('quantization_level'),'context':4096,'output_cap':160,'probes':results,'quality_review':'NOT_RUN','note':'Fixed owner probes; generated answers were not retained. Elapsed time excludes browser, MCP, DLP and voice.'}))
'''

def main():
    preflight()
    result=subprocess.run(wsl_command('podman','exec','larpus-agent','python','-c',CODE),capture_output=True,check=True,timeout=420)
    if len(result.stdout)>65536:raise ValueError('Oversized benchmark receipt')
    report=json.loads(result.stdout)
    report['generated_at']=timestamp()
    write_json(ROOT/'data/models/qwen35-gpu-benchmark.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

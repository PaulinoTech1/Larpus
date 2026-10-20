"""Fixed local SkillSpector targets, immutable input fingerprint, no cloud mode."""
import asyncio
import json
import os
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from mcp import Client
from runtime.mcp_client import child_parameters
from runtime.skills import ROOT, load_skills

DATA=ROOT/('release-state/security' if (ROOT/'deployment.json').is_file() else 'data/security')
APPROVED=ROOT/'config/mcp-approved.json'
SCAN_LOCK=threading.Lock()

def timestamp():
    return datetime.now(timezone.utc).isoformat()

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)

def fingerprint():
    from runtime.source_integrity import fingerprint as source_fingerprint
    return source_fingerprint(ROOT)

async def discover_async():
    async with Client(child_parameters(),read_timeout_seconds=10) as client:
        result=await client.list_tools()
        return sorted([t.model_dump(mode='json',exclude_none=True) for t in result.tools],key=lambda t:t['name'])

def discover():
    return asyncio.run(asyncio.wait_for(discover_async(),timeout=20))

def scan(descriptors):
    with SCAN_LOCK:
        before=fingerprint()
        skills=load_skills()
        DATA.mkdir(parents=True,exist_ok=True)
        target=DATA/'mcp-input'
        target.mkdir(exist_ok=True)
        capabilities=json.loads((ROOT/'config/mcp-capabilities.json').read_text(encoding='utf-8'))
        (target/'SKILL.md').write_text('---\nname: larpus-mcp\ndescription: Local Larpus MCP server inventory and source.\npermissions: '+json.dumps(capabilities['permissions'])+'\n---\n\n# Local MCP inventory\n\n'+json.dumps(descriptors,indent=2)+'\n\n# Declared scope (documentation, not an OS grant)\n'+json.dumps(capabilities,indent=2),encoding='utf-8')
        # Only fixed source files; never include credentials, recordings or prompts.
        for name in ('source_integrity.py','execution_profiles.py','execution_trace.py','execution_preflight.py','isolation_probe.py','mcp_server.py','mcp_skills.py','skill_resources.py','skills.py','mcp_client.py','local_ollama.py','inference.py','dlp.py','isolation.py','namespace_probe.py','knowledge.py','context.py','inference_broker.py','broker_scheduler.py','notes_worker.py','provenance.py','diagnostics.py','retrieval.py','retrieval_worker.py','scoring_pipeline.py','native_scoring.py','optimized_scoring.py'):
            shutil.copyfile(ROOT/'runtime'/name,target/name)
        (target/'scripts').mkdir(exist_ok=True)
        shutil.copyfile(ROOT/'scripts/protect-quarantine.ps1',target/'scripts/protect-quarantine.ps1')
        (target/'config').mkdir(exist_ok=True)
        shutil.copyfile(ROOT/'config/dlp.json',target/'config/dlp.json')
        executable=Path(os.environ.get('LARPUS_SCANNER_PYTHON',str(ROOT/'vendor/skillspector-env/Scripts/python.exe')))
        targets=[(identifier,ROOT/'skills'/identifier) for identifier in skills]+[('mcp',target)]
        results=[]
        env={k:os.environ[k] for k in ('SYSTEMROOT','WINDIR','PATH','TEMP','TMP','HOME','USERPROFILE') if k in os.environ}
        env.update({'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','OTEL_SDK_DISABLED':'true','LANGSMITH_TRACING':'false'})
        for identifier,directory in targets:
            report_path=DATA/(identifier+'.json')
            item={'target':identifier,'status':'error'}
            try:
                # Remove stale evidence first; a failed scan must not reuse it.
                report_path.unlink(missing_ok=True)
                process=subprocess.run([str(executable),str(ROOT/'scripts/offline_skillspector.py'),'scan',str(directory),'--no-llm','--format','json','--output',str(report_path)],cwd=ROOT,env=env,capture_output=True,timeout=90)
                if process.returncode not in (0,1,2) or not report_path.exists() or report_path.stat().st_size>10_000_000:
                    raise ValueError('Scanner did not produce a bounded report')
                report=json.loads(report_path.read_text(encoding='utf-8'))
                complete=report.get('analysis_completeness',{}).get('is_complete') is True and report.get('execution_successful') is True
                metadata=report.get('metadata',{})
                if metadata.get('llm_requested') is not False or metadata.get('inference_usage'):
                    raise ValueError('Scanner was not static-only')
                risk=report['risk_assessment']
                item.update({'status':'pass' if complete and risk['severity']=='LOW' and not report.get('issues') else 'warning','complete':complete,'severity':risk['severity'],'score':risk['score'],'issues':len(report.get('issues',[])),'report':str(report_path.relative_to(ROOT)).replace('\\','/')})
            except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired):
                item['message']='Scanner missing, failed, or incomplete report; not a clean scan'
            results.append(item)
        result={'generated_at':timestamp(),'fingerprint':before,'scanner':'SkillSpector 2.12.0','source_commit':'3c8e4b958fda9602e0044885f766be0e49f03585','mode':'static-no-network-wrapper','results':results}
        if fingerprint()!=before:
            result['status']='error'
            result['message']='Scan input changed during analysis'
        else:
            result['status']='pass' if all(r['status']=='pass' for r in results) else 'warning'
        write_json(DATA/'summary.json',result)
        return result

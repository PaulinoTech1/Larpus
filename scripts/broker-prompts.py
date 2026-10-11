"""Owner-only generation/check of allowed system-template hashes; no inference."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def manifest():
    from runtime.agents import load_personas
    from runtime.skills import selected_prompt
    from runtime.text_filter import DEFENSE_PROMPT
    from runtime.knowledge import EVIDENCE_PROMPT,PROTECTED_PROMPT,NO_EVIDENCE_PROMPT
    from runtime.context import SUMMARY_SYSTEM
    notes=runpy.run_path(str(ROOT/'scripts/study-notes.py'))
    chat={SUMMARY_SYSTEM}
    for persona in load_personas().values():
        for skill in [None,*persona.get('skills',[])]:
            base=persona['system_prompt']+selected_prompt(persona,skill)+DEFENSE_PROMPT+EVIDENCE_PROMPT
            for protected in ('',PROTECTED_PROMPT):
                for absent in ('',NO_EVIDENCE_PROMPT):chat.add(base+protected+absent)
    background={notes['FACT_PROMPT'],notes['ASK'],notes['ANSWER']}
    background.update(notes['PROMPT'].replace('{n}',str(n)) for n in range(1,16))
    digest=lambda values:sorted(hashlib.sha256(value.encode()).hexdigest() for value in values)
    return {'version':1,'chat':digest(chat),'notes':digest(background)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    path=ROOT/'config/broker-prompts.json';expected=manifest()
    if args.check:
        if json.loads(path.read_text())!=expected:raise SystemExit('Broker prompt manifest drift; regenerate before staging')
    else:path.write_text(json.dumps(expected,indent=2)+'\n',encoding='utf8')
    print('Approved system hashes:',{lane:len(expected[lane]) for lane in ('chat','notes')})
if __name__=='__main__':main()

"""Offline AST decision/import accounting. Measures only owned Python source."""
import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
BASELINE=ROOT/'config/complexity-baseline.json'

class Decisions(ast.NodeVisitor):
    def __init__(self):self.count=1
    def visit_FunctionDef(self,node):pass
    visit_AsyncFunctionDef=visit_FunctionDef
    def visit_Lambda(self,node):pass
    def generic_visit(self,node):
        if isinstance(node,(ast.If,ast.IfExp,ast.For,ast.AsyncFor,ast.While,ast.ExceptHandler)):self.count+=1
        if isinstance(node,ast.BoolOp):self.count+=len(node.values)-1
        if isinstance(node,ast.comprehension):self.count+=1+len(node.ifs)
        if isinstance(node,ast.Match):self.count+=sum(not isinstance(c.pattern,ast.MatchAs) or c.pattern.pattern is not None or c.pattern.name is not None for c in node.cases)
        super().generic_visit(node)

class Functions(ast.NodeVisitor):
    def __init__(self,path):self.path=path;self.parents=[];self.rows=[]
    def visit_ClassDef(self,node):
        self.parents.append(node.name);self.generic_visit(node);self.parents.pop()
    def visit_FunctionDef(self,node):
        name='.'.join(self.parents+[node.name]);decisions=Decisions()
        for child in node.body:decisions.visit(child)
        self.rows.append({'key':self.path+':'+name,'file':self.path,'function':name,'line':node.lineno,
                          'lines':node.end_lineno-node.lineno+1,'decisions':decisions.count})
        self.parents.append(node.name);self.generic_visit(node);self.parents.pop()
    visit_AsyncFunctionDef=visit_FunctionDef

def analyze(root=ROOT):
    files=sorted(p for folder in ('runtime','scripts') for p in (root/folder).glob('*.py'))
    paths={p.relative_to(root).as_posix().removesuffix('.py').replace('/','.') for p in files}
    functions=[];dependencies=[]
    for path in files:
        relative=path.relative_to(root).as_posix();tree=ast.parse(path.read_text(encoding='utf-8-sig'),filename=relative)
        visitor=Functions(relative);visitor.visit(tree);functions.extend(visitor.rows)
        top={id(n) for n in tree.body};imports={}
        for node in ast.walk(tree):
            targets=[]
            if isinstance(node,ast.Import):targets=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):
                prefix=node.module or ''
                if node.level:prefix='.'.join(relative.removesuffix('.py').replace('/','.').split('.')[:-node.level])+('.'+prefix if prefix else '')
                targets=[prefix]+[prefix+'.'+a.name for a in node.names]
            for target in targets:
                if target in paths:imports[target]=imports.get(target,False) or id(node) in top
        module=relative.removesuffix('.py').replace('/','.')
        dependencies.extend({'from':module,'to':target,'top_level':top_level} for target,top_level in sorted(imports.items()))
    fan_in=Counter(e['to'] for e in dependencies);fan_out=Counter(e['from'] for e in dependencies)
    return {'schema':'larpus.complexity/v1','functions':functions,'imports':dependencies,
            'modules':[{'module':p,'fan_in':fan_in[p],'fan_out':fan_out[p]} for p in sorted(paths)],
            'not_checked':['JavaScript/PowerShell function complexity','dynamic imports/exec','runtime call frequencies','cross-process wait graphs'],
            'metric':'AST decision count:1 + branches/loops/handlers/boolean alternatives/comprehensions/non-default match cases. Nested functions measured separately; not a formal whole-program complexity proof.'}

def regressions(report,baseline):
    if baseline.get('version')!=1 or not isinstance(baseline.get('functions'),dict):raise ValueError('Invalid complexity baseline')
    errors=[]
    for row in report['functions']:
        limit=baseline['functions'].get(row['key'],baseline['new_function'])
        for metric in ('decisions','lines'):
            if type(limit.get(metric)) is not int or limit[metric]<1:raise ValueError('Invalid complexity allowance')
            if row[metric]>limit[metric]:errors.append({'key':row['key'],'line':row['line'],'metric':metric,'actual':row[metric],'limit':limit[metric]})
    for row in report['modules']:
        limit=baseline.get('module_fan_out',{}).get(row['module'],6)
        if type(limit) is not int or limit<1:raise ValueError('Invalid import allowance')
        if row['fan_out']>limit:errors.append({'key':row['module'],'metric':'fan_out','actual':row['fan_out'],'limit':limit})
    return errors

def check(root=ROOT):
    report=analyze(root);baseline=json.loads((root/'config/complexity-baseline.json').read_text(encoding='utf8'))
    errors=regressions(report,baseline)
    if errors:
        raise ValueError('Complexity regression; refactor or explicitly review the allowance: '+json.dumps(errors))
    return report

def markdown(report):
    lines=['# Complexity inventory','',report['metric'],'','## Largest decision counts','',
           '| Function | Decisions | Lines |','| --- | ---: | ---: |']
    for row in sorted(report['functions'],key=lambda r:(-r['decisions'],-r['lines'],r['key']))[:25]:lines.append('| '+row['key']+' | '+str(row['decisions'])+' | '+str(row['lines'])+' |')
    lines+=['','## Highest import fan-in','', '| Module | Importers | Imports |','| --- | ---: | ---: |']
    for row in sorted(report['modules'],key=lambda r:(-r['fan_in'],r['module']))[:12]:lines.append('| '+row['module']+' | '+str(row['fan_in'])+' | '+str(row['fan_out'])+' |')
    lines+=['','Not checked: '+', '.join(report['not_checked'])+'.','',
            'This is an inventory, not a quality score. High counts are review targets. Baseline allowances retain visible existing debt; new functions default to 12 decisions/80 lines. Do not reset the baseline to bypass a failure.']
    return '\n'.join(lines)+'\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['report','check','baseline']);p.add_argument('--reason');p.add_argument('--output',type=Path,default=ROOT/'data/complexity/latest.json');p.add_argument('--markdown',type=Path);a=p.parse_args()
    report=analyze()
    if a.action=='baseline':
        if not a.reason or len(a.reason)<20:raise SystemExit('A reviewed reason of at least 20 characters is required')
        value={'version':1,'reason':a.reason,'new_function':{'decisions':12,'lines':80},
               'module_fan_out':{r['module']:max(4,r['fan_out']) for r in report['modules']},
               'functions':{r['key']:{'decisions':max(12,r['decisions']),'lines':max(80,r['lines'])} for r in report['functions']}}
        BASELINE.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
    if a.action=='check':
        errors=regressions(report,json.loads(BASELINE.read_text(encoding='utf8')))
        if errors:
            print(json.dumps({'status':'FAIL','regressions':errors}),file=sys.stderr);return 1
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if a.markdown:a.markdown.write_text(markdown(report),encoding='utf8')
    print(json.dumps({'status':'PASS' if a.action=='check' else 'measured','functions':len(report['functions']),'modules':len(report['modules']),'report':str(a.output)}))
    return 0
if __name__=='__main__':raise SystemExit(main())

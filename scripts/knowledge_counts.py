"""Reconcile reviewed catalog passage counts with the selected local index."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sqlite3


def counts(root):
    source=root/'knowledge/approved.sqlite'
    if source.is_symlink() or not source.is_file():
        raise ValueError('Approved knowledge index is missing or redirected')
    path=source.resolve()
    passages=defaultdict(set)
    with sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        for source_id,url,locator,text in db.execute('SELECT source_id,url,locator,text FROM chunks'):
            passages[(source_id,url)].add((locator,text))
    return {key:len(value) for key,value in passages.items()}


def reconcile(root,write=False):
    path=root/'knowledge/sources.json'
    if path.is_symlink():raise ValueError('Knowledge catalog is redirected')
    catalog=json.loads(path.read_text(encoding='utf-8'))
    actual=counts(root)
    mismatches=[]
    for entry in catalog['documents']:
        if 'indexed_passages' not in entry:continue
        expected=actual.get((entry['id'],entry['url']),0)
        if entry['indexed_passages']!=expected:
            mismatches.append((entry['id'],entry['indexed_passages'],expected))
            if write:entry['indexed_passages']=expected
    if write and mismatches:
        path.write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
    elif mismatches:
        raise ValueError('Knowledge catalog passage count mismatch: '+repr(mismatches[:10]))
    return mismatches


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path,help='Source tree whose approved index and catalog are paired')
    parser.add_argument('--write',action='store_true',help='Update declared counts in this source tree')
    args=parser.parse_args()
    result=reconcile(args.root,args.write)
    print(json.dumps({'root':str(args.root),'updated' if args.write else 'mismatches':result}))


if __name__=='__main__':main()

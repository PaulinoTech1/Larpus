import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('review_release',Path(__file__).resolve().parents[1]/'scripts/releases.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class ReviewGateTests(unittest.TestCase):
    def test_review_is_exact_and_source_pinned_and_never_hides_warning(self):
        issue=lambda file:{'category':'Execution','pattern':'fixed probe','severity':'MEDIUM','location':{'file':file}}
        baseline={'issues':[issue('old.py')]};report={'issues':[issue('old.py'),issue('notes_worker.py')]}
        entries=lambda v:[{'category':c,'pattern':p,'severity':s,'file':f,'count':n} for (c,p,s,f),n in r.issue_signatures(v).items()]
        review={'version':1,'reason':'New fixed owner probe reviewed, warning retained','previous':entries(baseline),'approved':entries(report),'sources':{'runtime/notes_worker.py':'a'*64}}
        summary={'status':'warning','results':[{'target':name,'complete':True,'status':'pass' if name!='mcp' else 'warning'} for name in ('skill','mcp')]}
        r.scan_gate(summary,report,baseline,['skill','mcp'],review,review['sources'])
        for sources in (None,{}, {'runtime/notes_worker.py':'b'*64}):
            with self.assertRaises(ValueError):r.scan_gate(summary,report,baseline,['skill','mcp'],review,sources)
        for changed in ({'issues':report['issues']+[issue('extra.py')]},{'issues':[]}):
            with self.assertRaises(ValueError):r.scan_gate(summary,changed,baseline,['skill','mcp'],review,review['sources'])
        summary['results'][0]['status']='warning'
        with self.assertRaises(ValueError):r.scan_gate(summary,report,baseline,['skill','mcp'],review,review['sources'])

if __name__=='__main__':unittest.main()

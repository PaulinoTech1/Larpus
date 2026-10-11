import unittest
from scripts.research_policy import vet

GOOD={'id':'ok-entry','level':'phd','source_url':'https://dspace.mit.edu/handle/1','download_url':'https://dspace.mit.edu/x.pdf','degree_evidence_url':'https://dspace.mit.edu/handle/1','title':'T','authors':['A'],'year':'2024','rights':['r'],'degrees':['Ph.D.'],'full_text_status':'downloaded','sha256':'a'*64,'bytes':10}

class ResearchPolicyTests(unittest.TestCase):
    def test_reviewed_entry_passes(self):
        self.assertEqual(vet(dict(GOOD))['id'],'ok-entry')
    def test_unreviewed_or_unpinned_sources_are_refused(self):
        for change in ({'download_url':'https://example.com/x.pdf'},{'source_url':'http://dspace.mit.edu/handle/1'},
                       {'download_url':'https://user:pw@dspace.mit.edu/x.pdf'},{'sha256':None},{'bytes':0},
                       {'rights':[]},{'degrees':[]},{'level':'blog'},{'id':'../escape'},{'authors':[]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                vet({**GOOD,**change})
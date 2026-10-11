import unittest
from scripts.research_policy import vetted_host, vet

QSB='https://raw.githubusercontent.com/QubesOS/qubes-secpack/master/QSBs/qsb-001-2011.txt'
ENTRY={'id':'qsb','level':'references','source_url':QSB,'download_url':QSB,'degree_evidence_url':'https://www.qubes-os.org/security/qsb/',
       'title':'T','authors':['A'],'year':'2011','rights':['r'],'degrees':['ref'],'format':'txt','full_text_status':'downloaded','sha256':'a'*64,'bytes':10}

class PathPrefixTests(unittest.TestCase):
    def test_qubes_secpack_prefix_accepted(self):
        self.assertEqual(vetted_host(QSB),'raw.githubusercontent.com')
        self.assertEqual(vet(dict(ENTRY))['id'],'qsb')
    def test_other_raw_github_paths_refused(self):
        for url in ('https://raw.githubusercontent.com/attacker/qubes-secpack/master/x.txt',
                    'https://raw.githubusercontent.com/QubesOS/qubes-secpack-evil/master/x.txt',
                    'https://raw.githubusercontent.com/QubesOS/qubes-secpack',
                    'https://raw.githubusercontent.com/QubesOS/qubes-secpack/../../evil/x.txt',
                    'https://raw.githubusercontent.com/QubesOS/qubes-secpack/%2e%2e/evil/x.txt',
                    'https://raw.githubusercontent.com/QubesOS/qubes-secpack/x.txt?redirect=1',
                    'https://raw.githubusercontent.com/qubesos/qubes-secpack/master/x.txt',
                    'http://raw.githubusercontent.com/QubesOS/qubes-secpack/master/x.txt',
                    'https://github.com/QubesOS/qubes-secpack/blob/master/x.txt'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                vetted_host(url)
    def test_format_must_be_known(self):
        with self.assertRaises(ValueError):
            vet({**ENTRY,'format':'exe'})

if __name__=='__main__':
    unittest.main()

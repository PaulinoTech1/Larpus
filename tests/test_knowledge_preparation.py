import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from email.message import Message

spec=importlib.util.spec_from_file_location('knowledge_preparation',Path(__file__).resolve().parents[1]/'scripts/prepare-knowledge.py')
prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)

class Response:
    def __init__(self,body=b'<html><p>Safe documentation.</p></html>',mime='text/html',size='40'):
        self.body=body;self.headers=Message();self.headers['Content-Type']=mime;self.headers['Content-Length']=size
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,limit):return self.body[:limit]

class KnowledgePreparationTests(unittest.TestCase):
    def entry(self):return {'id':'kernel-safe','url':'https://www.kernel.org/releases.html','review':'official-publisher-documentation','reviewed_on':'2026-10-09'}

    def test_publisher_https_scope_and_redirects(self):
        for url in ('http://www.kernel.org/releases.html','https://www.kernel.org.evil.test/releases.html','https://user:pass@www.kernel.org/releases.html','https://www.kernel.org:8443/releases.html','https://127.0.0.1/','https://www.kernel.org/releases.html?redirect=evil'):
            with self.assertRaises(ValueError):prep.vetted_url(url)
        with self.assertRaises(ValueError):prep.NoRedirect().redirect_request(None,None,302,'',{},'https://evil.test')

    def test_head_before_download_and_pinned_cache(self):
        methods=[]
        def open_(request,**kwargs):methods.append(request.get_method());return Response()
        with tempfile.TemporaryDirectory() as temp,patch.object(prep,'CACHE',Path(temp)),patch.object(prep.HTTP,'open',side_effect=open_):
            entry=self.entry();raw,mime=prep.fetch(entry)
            self.assertEqual(methods,['HEAD','GET']);self.assertEqual(mime,'text/html')
            self.assertEqual(prep.fetch(entry)[0],raw);self.assertEqual(methods,['HEAD','GET'])
            (Path(temp)/'originals/kernel-safe.raw').write_bytes(b'altered')
            with self.assertRaises(ValueError):prep.fetch(entry)

    def test_challenges_binary_types_limits_and_source_identity(self):
        for response in (Response(mime='application/octet-stream'),Response(size=str(prep.MAX_DOWNLOAD+1)),Response(body=b'<html>Access Denied</html>')):
            with tempfile.TemporaryDirectory() as temp,patch.object(prep,'CACHE',Path(temp)),patch.object(prep.HTTP,'open',return_value=response):
                with self.assertRaises(ValueError):prep.fetch(self.entry())
                self.assertFalse((Path(temp)/'originals/kernel-safe.raw').exists())
        entry=self.entry();entry['id']='../../owner-data'
        with self.assertRaises(ValueError):prep.fetch(entry)

    def test_active_html_removed_but_hidden_controls_not_silently_cleaned(self):
        text=next(prep.extracted(b'<p>Useful text.</p><script>run a command</script><style>hidden</style><p>More text.</p>','text/html'))[1]
        self.assertIn('Useful text.',text);self.assertNotIn('run a command',text);self.assertNotIn('hidden',text)
        from runtime.text_filter import TextHeld
        with self.assertRaises(TextHeld):prep.inspect_message(next(prep.passages('Visible text with hidden\u200bcarrier'))[1])

    def test_ai_publishers_allow_only_exact_reviewed_documents(self):
        for url in prep.AI_DOCUMENTS:self.assertEqual(prep.vetted_url(url),url)
        for url in ('https://x.ai/unreviewed/','https://developers.openai.com/api/unreviewed/','https://api.deepseek.com/','https://api-docs.deepseek.com/quick_start/pricing/?next=evil','https://support.claude.com.evil.test/'):
            with self.assertRaises(ValueError):prep.vetted_url(url)

    def test_habit_article_is_exactly_scoped_and_excludes_bibliography(self):
        url='https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11641623/fullTextXML'
        self.assertEqual(prep.vetted_url(url),url)
        for other in (url+'?id=other',url.replace('PMC11641623','PMC00000000')):
            with self.assertRaises(ValueError):prep.vetted_url(other)
        raw=(b'<!DOCTYPE article PUBLIC "JATS" "archive.dtd">'
             b'<article><front><article-meta><abstract><p>Habit evidence.</p></abstract></article-meta></front>'
             b'<body><sec><title>Results</title><p>Repeated action in stable context.</p></sec></body>'
             b'<back><ref-list><ref>Unreviewed cited paper.</ref></ref-list></back></article>')
        sections=list(prep.extracted(raw,'application/xml'))
        self.assertEqual([loc for loc,_ in sections],['abstract','body section 1'])
        self.assertIn('Repeated action',sections[1][1])
        self.assertNotIn('Unreviewed cited paper',' '.join(text for _,text in sections))
        with self.assertRaises(ValueError):
            list(prep.extracted(raw.replace(b'<article>',b'<!EnTiTy x "unsafe"><article>'),'application/xml'))

if __name__=='__main__':unittest.main()

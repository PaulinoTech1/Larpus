import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from runtime import knowledge,retrieval

ROOT=Path(__file__).resolve().parents[1]

def library(root,rows):
    database=root/'approved.sqlite'
    with sqlite3.connect(database) as db:
        db.execute("CREATE VIRTUAL TABLE chunks USING fts5(source_id UNINDEXED,title,url UNINDEXED,snapshot UNINDEXED,locator UNINDEXED,text,role UNINDEXED,tokenize='porter unicode61')")
        db.executemany('INSERT INTO chunks VALUES (?,?,?,?,?,?,?)',rows)
    db.close()
    (root/'manifest.json').write_text(json.dumps({'version':1,'database_sha256':hashlib.sha256(database.read_bytes()).hexdigest(),'database_bytes':database.stat().st_size}))

ROWS=[
    ('game-a','Game strategy notes','https://example.org/a','2026-10-09','offset 0','Players bluff and anticipate opponent moves in poker and chess strategy games.','psychologist'),
    ('game-b','Board game overview','https://example.org/b','2026-10-09','offset 0','A board game catalogue lists games, prices and opponents counts.','psychologist'),
    ('theory-c','Theory of mind','https://example.org/c','2026-10-09','offset 0','Theory of mind lets a person model what another person believes and intends.','psychologist'),
]

class FakeEngine:
    """Deterministic stand-in: rerank by keyword, neighbours by fixed rowids."""
    bm25=12;semantic=8;batch=4;deadline=5.0;minimum=0.0
    def __init__(self,neighbors=(),weights=None):self._neighbors=list(neighbors);self.weights=weights or {};self.neighbor_calls=0
    def neighbors(self,question,limit):self.neighbor_calls+=1;return self._neighbors[:limit]
    def rerank(self,question,passages,deadline=None):
        return [sum(w for k,w in self.weights.items() if k in p.casefold())-1.0 for p in passages]

class CpuRetrievalTests(unittest.TestCase):
    def setUp(self):retrieval.reset()
    def tearDown(self):retrieval.reset()

    def test_manifest_pins_revisions_hashes_and_versions(self):
        config=retrieval.load_config()
        self.assertEqual(config['models']['embedder']['revision'],'5c38ec7c405ec4b44b94cc5a9bb96e735b38267a')
        self.assertEqual(config['models']['reranker']['revision'],'2cfc18c9415c912f9d8155881c133215df768a70')
        self.assertEqual({n:p['version'] for n,p in config['packages'].items()},{'onnxruntime':'1.23.2','tokenizers':'0.23.3','numpy':'2.2.6'})
        pins=(ROOT/'requirements-retrieval.txt').read_text()
        for package in config['packages'].values():
            for wheel in package['wheels'].values():self.assertIn(wheel['sha256'],pins)

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model.onnx';path.write_bytes(b'tampered!')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                retrieval.verify_file(path,{'sha256':hashlib.sha256(b'original!').hexdigest(),'bytes':9})
            with self.assertRaisesRegex(ValueError,'size mismatch'):
                retrieval.verify_file(path,{'sha256':hashlib.sha256(b'tampered!').hexdigest(),'bytes':10})
            self.assertEqual(retrieval.verify_file(path,{'sha256':hashlib.sha256(b'tampered!').hexdigest(),'bytes':9}),path)
            config=retrieval.load_config()
            for spec in config['models']['embedder']['files'].values():spec['bytes']=9
            (Path(directory)/'bge-small-en-v1.5').mkdir()
            for name in config['models']['embedder']['files']:(Path(directory)/'bge-small-en-v1.5'/name).write_bytes(b'tampered!')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):retrieval.verify_model(config,'embedder',directory)

    def test_engine_unavailable_without_index_or_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);library(root,ROWS)
            self.assertIsNone(retrieval.engine(root))
            self.assertEqual(retrieval.status(root)['cpu_retrieval'],'bm25-only')
            with patch.object(retrieval,'MODELS',root/'absent'):
                (root/'embeddings-manifest.json').write_text('{}')
                retrieval.reset();self.assertIsNone(retrieval.engine(root))

    def test_index_must_match_approved_database(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);library(root,ROWS);config=retrieval.load_config()
            embedder=config['models']['embedder']
            (root/'embeddings-manifest.json').write_text(json.dumps({'version':1,'database_sha256':'0'*64,'embedder_revision':embedder['revision'],'embedder_sha256':embedder['files']['model.onnx']['sha256']}))
            with self.assertRaisesRegex(ValueError,'does not match approved database'):retrieval.load_index(root,config)

    def test_fallback_without_models_matches_bm25(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);library(root,ROWS)
            with patch.object(knowledge,'DIRECTORY',root):
                hybrid=knowledge.retrieve('psychologist','How do players anticipate opponents in games?')
                with patch.dict('os.environ',{'LARPUS_CPU_RETRIEVAL':'off'}):
                    retrieval.reset();plain=knowledge.retrieve('psychologist','How do players anticipate opponents in games?')
            self.assertTrue(plain);self.assertEqual(hybrid,plain)

    def test_engine_failure_keeps_bm25_order(self):
        class Broken(FakeEngine):
            def rerank(self,*args,**kwargs):raise RuntimeError('onnx failure')
        rows=[('a','t','u','s','l1','one'),('b','t','u','s','l2','two')]
        with patch.object(knowledge,'_engine',return_value=Broken()):
            self.assertEqual(knowledge._hybrid('q',rows,False),rows)

    def test_reranker_orders_candidates_and_adds_semantic_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);library(root,ROWS)
            # BM25 alone prefers the keyword-heavy catalogue; theory-c only matches semantically.
            engine=FakeEngine(neighbors=[3,1],weights={'bluff':3.0,'theory of mind':2.0})
            with patch.object(knowledge,'DIRECTORY',root),patch.object(knowledge,'_engine',return_value=engine):
                found=knowledge._retrieve('psychologist','how do people outthink opponents in games',9000)
            self.assertEqual([f['id'] for f in found],['game-a','theory-c','game-b'])
            self.assertEqual(engine.neighbor_calls,1)

    def test_low_scoring_semantic_only_passages_are_dropped(self):
        rows=[('a','t','u','s','l1','alpha')]
        engine=FakeEngine(weights={'alpha':2.0})
        with patch.object(knowledge,'_engine',return_value=engine),patch.object(knowledge,'database') as database:
            database.return_value.__enter__=lambda s:s
            connection=database.return_value;connection.execute.return_value=[(7,'z','t','u','s','l9','unrelated')]
            engine._neighbors=[7]
            self.assertEqual([r[0] for r in knowledge._hybrid('q',rows,False)],['a'])

    def test_constrained_questions_never_add_semantic_rows(self):
        rows=[('a','t','u','s','l1','alpha'),('b','t','u','s','l2','beta')]
        engine=FakeEngine(neighbors=[9],weights={'beta':5.0})
        with patch.object(knowledge,'_engine',return_value=engine):
            self.assertEqual([r[0] for r in knowledge._hybrid('kernel 6.1 question',rows,True)],['b','a'])
        self.assertEqual(engine.neighbor_calls,0)

    def test_deadline_leaves_unscored_candidates_in_bm25_order(self):
        rows=[('a','t','u','s','l1','x'),('b','t','u','s','l2','y'),('c','t','u','s','l3','z')]
        class Slow(FakeEngine):
            def rerank(self,question,passages,deadline=None):return [None,2.0,None]
        with patch.object(knowledge,'_engine',return_value=Slow()):
            self.assertEqual([r[0] for r in knowledge._hybrid('q',rows,True)],['b','a','c'])

class ContainerLimitTests(unittest.TestCase):
    def test_agent_container_limits_raised_everywhere(self):
        spec=importlib.util.spec_from_file_location('releases_limits',ROOT/'scripts/releases.py')
        release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
        self.assertEqual(release.AGENT_LIMITS,('--pids-limit=64','--memory=12g','--cpus=8'))
        self.assertIn('*AGENT_LIMITS',(ROOT/'scripts/releases.py').read_text(encoding='utf-8'))
        deploy=(ROOT/'deploy/windows-home/deploy.sh').read_text(encoding='utf-8')
        self.assertIn('--pids-limit=64 --memory=12g --cpus=8',deploy)
        self.assertNotIn('--memory=1g',deploy)

    def test_release_payload_excludes_embedding_build_temporaries(self):
        spec=importlib.util.spec_from_file_location('releases_payload',ROOT/'scripts/releases.py')
        release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'knowledge').mkdir()
            for name in ('embeddings.npy','embeddings.build.npy','notes.build.sqlite-journal'):(root/'knowledge'/name).write_bytes(b'x')
            self.assertEqual(set(release.payload(root)),{'knowledge/embeddings.npy'})

    def test_image_installs_pinned_runtime_without_dependencies(self):
        containerfile=(ROOT/'deploy/windows-home/Containerfile').read_text(encoding='utf-8')
        self.assertIn('--no-index --no-deps --find-links=/wheels onnxruntime==1.23.2 tokenizers==0.23.3 numpy==2.2.6',containerfile)
        self.assertIn('!vendor/retrieval-models/**',(ROOT/'.containerignore').read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main()
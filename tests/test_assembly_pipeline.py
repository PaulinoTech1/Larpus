import unittest
from unittest.mock import patch
try:import numpy as np
except ImportError:np=None
from runtime import scoring_pipeline
from runtime import retrieval_worker

@unittest.skipIf(np is None,'Optional NumPy retrieval dependency is not installed')
class AssemblyPipelineTests(unittest.TestCase):
 def test_unavailable_native_uses_numpy_and_explains_selection(self):
  vectors=np.eye(3,dtype=np.float32)
  with patch.object(scoring_pipeline,'NativeScorer',side_effect=OSError('missing')):
   scorer=scoring_pipeline.Pipeline(vectors,preferred="assembly")
  self.assertEqual(scorer.status()['active_id'],'numpy')
  self.assertNotIn('error',scorer.status(),'Successful worker responses must not use the reserved transport error key')
  np.testing.assert_array_equal(scorer.score(np.ones(3,dtype=np.float32)),np.ones(3))
  with self.assertRaises(ValueError):scorer.select('assembly')

 def test_switch_and_failure_keep_valid_numpy_scores(self):
  class Native:
   def __init__(self,vectors):self.vectors=vectors
   def score(self,q):return self.vectors@q
  with patch.object(scoring_pipeline,'NativeScorer',Native):scorer=scoring_pipeline.Pipeline(np.eye(4,dtype=np.float32),preferred="assembly")
  self.assertEqual(scorer.status()['active_id'],'assembly')
  scorer.select('assembly');self.assertEqual(scorer.status()['active_id'],'assembly')
  scorer.select('numpy');self.assertEqual(scorer.status()['active_id'],'numpy')
  scorer.select('assembly')
  with patch.object(scorer.native,'score',side_effect=RuntimeError('bad')):
   np.testing.assert_array_equal(scorer.score(np.ones(4,dtype=np.float32)),np.ones(4))
  self.assertEqual(scorer.status()['active_id'],'numpy')
  self.assertTrue(scorer.status()['notice'])
  with self.assertRaises(ValueError):scorer.select('../other')

 def test_control_protocol_is_strict_and_not_a_new_chat_tool(self):
  self.assertEqual(retrieval_worker.validate({'action':'pipeline'})['action'],'pipeline')
  self.assertEqual(retrieval_worker.validate({'action':'pipeline','pipeline_id':'numpy'})['pipeline_id'],'numpy')
  for bad in ({'action':'pipeline','pipeline_id':'x'},{'action':'pipeline','path':'x'},{'action':'pipeline','pipeline_id':True}):
   with self.assertRaises(ValueError):retrieval_worker.validate(bad)

 def test_nearly_tied_scores_use_original_numpy(self):
  class Native:
   def __init__(self,vectors):pass
   def score(self,q):return np.array([1+1e-7,1],dtype=np.float32)
  with patch.object(scoring_pipeline,'NativeScorer',Native):scorer=scoring_pipeline.Pipeline(np.eye(2,dtype=np.float32),preferred="assembly")
  scorer.select('assembly')
  q=np.array([1,1+1e-7],dtype=np.float32)
  np.testing.assert_array_equal(scorer.score(q,limit=1),q)
  self.assertEqual(scorer.status()['last_used'],'numpy')
  self.assertEqual(scorer.status()['ambiguity_fallbacks'],1)

 def test_interior_near_ties_may_reorder_without_numpy_recheck(self):
  class Native:
   def __init__(self,vectors):pass
   def score(self,q):return np.array([1+1e-7,1,0],dtype=np.float32)
  with patch.object(scoring_pipeline,'NativeScorer',Native):scorer=scoring_pipeline.Pipeline(np.eye(3,dtype=np.float32),preferred="assembly")
  scorer.select('assembly');q=np.array([1,1+1e-7,0],dtype=np.float32)
  np.testing.assert_allclose(scorer.score(q,limit=2),q,atol=2e-6,rtol=2e-5)
  self.assertEqual(scorer.status()['last_used'],'assembly')
  self.assertEqual(scorer.status()['ambiguity_fallbacks'],0)

 def test_native_source_manifest_and_binary_are_in_scan_fingerprint(self):
  import tempfile
  from pathlib import Path
  from runtime import security_scan
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);native=root/'runtime/native';native.mkdir(parents=True)
   with patch.object(security_scan,'ROOT',root),patch.object(security_scan,'APPROVED',root/'config/mcp-approved.json'):
    previous=security_scan.fingerprint()
    for name in ('score_half.S','manifest.json','liblarpus_score.so'):
     (native/name).write_bytes(b'new bytes')
     current=security_scan.fingerprint();self.assertNotEqual(current,previous);previous=current

 def test_cutoff_guard_uses_empirical_tolerance_and_scales_with_query(self):
  with patch.object(scoring_pipeline,'NativeScorer',side_effect=OSError('missing')):
   scorer=scoring_pipeline.Pipeline(np.eye(384,dtype=np.float32),preferred="assembly")
  scores=np.zeros(384,dtype=np.float32);scores[0]=1;scores[1]=1-1e-5
  query=np.zeros(384,dtype=np.float32);query[0]=1
  self.assertFalse(scorer._ambiguous(scores,query,1))
  scores[1]=1-1e-6
  self.assertTrue(scorer._ambiguous(scores,query,1))
  self.assertTrue(scorer._ambiguous(scores*10,query*10,1))


if __name__=='__main__':unittest.main()

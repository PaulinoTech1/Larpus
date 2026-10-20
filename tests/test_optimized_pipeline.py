import unittest
from unittest.mock import patch
import numpy as np
from runtime import scoring_pipeline as sp
from runtime.retrieval_worker import validate

class Fake:
 def __init__(self,vectors):self.vectors=vectors;self.closed=False
 def score(self,q):return self.vectors@q
 def close(self):self.closed=True

class OptimizedPipelineTests(unittest.TestCase):
 def make(self,vectors=None):
  with patch.object(sp,'NativeScorer',Fake),patch.object(sp,'OptimizedScorer',Fake):
   return sp.Pipeline(np.eye(4,dtype='float32') if vectors is None else vectors)
 def test_default_and_all_three_switches(self):
  p=self.make()
  self.assertEqual(p.status()['active_id'],'assembly-optimized')
  for name in ('numpy','assembly','assembly-optimized'):
   self.assertEqual(p.select(name)['active_id'],name)
   np.testing.assert_array_equal(p.score(np.ones(4,dtype='float32')),np.ones(4))
   self.assertEqual(p.last_used,name)
   self.assertEqual(validate({'action':'pipeline','pipeline_id':name})['pipeline_id'],name)
 def test_failure_disables_only_optimized_and_uses_numpy(self):
  p=self.make();native=p.optimized
  with patch.object(native,'score',side_effect=RuntimeError('failed')):
   np.testing.assert_array_equal(p.score(np.ones(4,dtype='float32')),np.ones(4))
  self.assertTrue(native.closed)
  self.assertEqual(p.status()['active_id'],'numpy')
  self.assertEqual(p.select('assembly')['active_id'],'assembly')
  with self.assertRaises(ValueError):p.select('assembly-optimized')
 def test_duplicate_cutoff_uses_numpy_guard(self):
  p=self.make(np.ones((20,1),dtype='float32'))
  p.score(np.ones(1,dtype='float32'),18)
  self.assertEqual(p.last_used,'numpy');self.assertEqual(p.ambiguity_fallbacks,1)
 def test_original_keeps_duplicate_rows_on_assembly(self):
  p=self.make(np.ones((20,1),dtype='float32'));p.select('assembly')
  p.score(np.ones(1,dtype='float32'),18)
  self.assertEqual(p.last_used,'assembly');self.assertEqual(p.ambiguity_fallbacks,0)
 def test_missing_optimized_defaults_to_numpy(self):
  with patch.object(sp,'NativeScorer',Fake),patch.object(sp,'OptimizedScorer',side_effect=OSError('missing')):
   p=sp.Pipeline(np.eye(4,dtype='float32'))
  self.assertEqual(p.status()['active_id'],'numpy')
  self.assertTrue(p.status()['notice'])
 def test_close_releases_both_backends(self):
  p=self.make();a,b=p.native,p.optimized;p.close();p.close()
  self.assertTrue(a.closed and b.closed)
  self.assertEqual(p.status()['active_id'],'numpy')

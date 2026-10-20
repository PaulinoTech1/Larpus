import ctypes
from types import SimpleNamespace
import unittest
from unittest.mock import patch
try:import numpy as np
except ImportError:np=None
from runtime import native_scoring

class Kernel:
 def __call__(self,matrix,query,output,rows,dimension):
  half=np.ctypeslib.as_array(ctypes.cast(matrix,ctypes.POINTER(ctypes.c_uint16)),shape=(rows*dimension,)).view(np.float16)
  q=np.ctypeslib.as_array(ctypes.cast(query,ctypes.POINTER(ctypes.c_float)),shape=(dimension,))
  out=np.ctypeslib.as_array(ctypes.cast(output,ctypes.POINTER(ctypes.c_float)),shape=(rows,))
  out[:]=half.reshape(rows,dimension).astype(np.float32)@q
  return 0

@unittest.skipIf(np is None,'Optional NumPy is unavailable')
class NativeBufferTests(unittest.TestCase):
 def make(self,pool=None,vectors=None):
  from contextlib import ExitStack
  with ExitStack() as stack:
   stack.enter_context(patch.object(native_scoring.NativeScorer,'_library',return_value=SimpleNamespace(larpus_score_half=Kernel())))
   stack.enter_context(patch.object(native_scoring.NativeScorer,'_check',return_value=None))
   if pool is not None:stack.enter_context(patch.object(native_scoring,'ThreadPoolExecutor',return_value=pool))
   return native_scoring.NativeScorer(np.eye(4,dtype=np.float32) if vectors is None else vectors)

 def test_query_and_retained_outputs_survive_subsequent_calls(self):
  scorer=self.make()
  try:
   query=np.array([1,2,3,4],dtype=np.float32);saved=query.copy()
   first=scorer.score(query);second=scorer.score(-query)
   np.testing.assert_array_equal(query,saved)
   np.testing.assert_array_equal(first,saved)
   np.testing.assert_array_equal(second,-saved)
   self.assertFalse(np.shares_memory(first,second))
  finally:scorer.close()

 def test_partial_submit_failure_waits_for_inflight_buffer_users(self):
  class Future:
   waited=False
   def result(self):self.waited=True;return 0
  future=Future()
  class Pool:
   count=0
   def submit(self,*args):
    self.count+=1
    if self.count>1:raise RuntimeError('executor stopped')
    return future
  scorer=self.make(Pool())
  with self.assertRaises(RuntimeError):scorer.score(np.ones(4,dtype=np.float32))
  self.assertTrue(future.waited,'Native writes must finish before output buffers can be released')

 def test_cached_ranges_cover_empty_short_and_uneven_matrices(self):
  for rows in (0,1,2,3,17):
   matrix=np.arange(rows*7,dtype=np.float32).reshape(rows,7)/8
   scorer=self.make(vectors=matrix)
   try:np.testing.assert_array_equal(scorer.score(np.ones(7,dtype=np.float32)),matrix.sum(axis=1))
   finally:scorer.close()

if __name__=='__main__':unittest.main()

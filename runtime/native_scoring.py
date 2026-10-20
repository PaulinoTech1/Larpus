"""Pinned optional Linux assembly scorer. Never downloads or compiles at runtime."""
import ctypes
import hashlib
import json
import platform
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

class NativeScorer:
 @staticmethod
 def _library(manifest_name='manifest.json',library_name='liblarpus_score.so'):
  import numpy as np
  flags=np._core._multiarray_umath.__cpu_features__
  if sys.platform!='linux' or platform.machine()!='x86_64' or not all(flags.get(k) for k in ('AVX2','FMA3','F16C')):
   raise OSError('Assembly requires Linux x86-64 AVX2/FMA/F16C')
  directory=Path(__file__).parent/'native';manifest=directory/manifest_name;library=directory/library_name
  if manifest.is_symlink() or library.is_symlink() or manifest.stat().st_size>4096:raise ValueError('Invalid assembly artifact')
  spec=json.loads(manifest.read_text())
  if spec.get('version')!=1 or library.stat().st_size!=spec['bytes'] or hashlib.sha256(library.read_bytes()).hexdigest()!=spec['sha256']:
   raise ValueError('Assembly artifact pin mismatch')
  return ctypes.CDLL(str(library))

 def __init__(self,vectors):
  import numpy as np
  self.library=self._library()
  if vectors.dtype!=np.float32 or vectors.ndim!=2 or vectors.shape[1]<1 or not np.isfinite(vectors).all():raise ValueError('Invalid vector matrix')
  self.vectors=np.ascontiguousarray(vectors,dtype=np.float16)
  if not np.array_equal(self.vectors.astype(np.float32),vectors):raise ValueError('Index is not exact binary16 data')
  self.vectors.flags.writeable=False
  self.function=self.library.larpus_score_half
  self.function.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t]
  self.function.restype=ctypes.c_int
  n,d=self.vectors.shape;base=self.vectors.ctypes.data
  starts=tuple(n*part//4 for part in range(5))
  self.partitions=tuple((base+start*d*2,start,end-start) for start,end in zip(starts,starts[1:]) if end>start)
  self.pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix='assembly-score')
  try:self._check(vectors)
  except Exception:self.pool.shutdown(wait=True);raise

 def close(self):self.pool.shutdown(wait=True)

 def _check(self,reference):
  import numpy as np
  if not len(reference):return
  rng=np.random.default_rng(5900)
  for q in rng.normal(size=(3,reference.shape[1])).astype(np.float32):
   q/=np.linalg.norm(q);actual=self.score(q);expected=reference@q
   np.testing.assert_allclose(actual,expected,atol=2e-6,rtol=2e-5)
   if set(self._top(actual))!=set(self._top(expected)):raise ValueError('Assembly startup candidate validation failed')

 @staticmethod
 def _top(scores):
  import numpy as np
  k=min(18,len(scores))
  if not k:return []
  indices=np.argpartition(-scores,k-1)[:k]
  return indices[np.argsort(-scores[indices],kind='stable')].tolist()

 def score(self,query):
  import numpy as np
  if query.dtype!=np.float32 or query.shape!=(self.vectors.shape[1],) or not query.flags.c_contiguous or not np.isfinite(query).all():
   raise ValueError('Invalid assembly query')
  result=np.empty(len(self.vectors),dtype=np.float32)
  d=self.vectors.shape[1];futures=[];failed=False
  qptr=query.ctypes.data;optr=result.ctypes.data
  try:
   for matrix,start,rows in self.partitions:
    futures.append(self.pool.submit(self.function,matrix,qptr,optr+start*4,rows,d))
  except Exception:failed=True
  # Wait for every partition even on errors; buffers remain live until all work ends.
  for future in futures:
   try:failed|=future.result()!=0
   except Exception:failed=True
  if failed or not np.isfinite(result).all():raise RuntimeError('Assembly scoring failed')
  return result

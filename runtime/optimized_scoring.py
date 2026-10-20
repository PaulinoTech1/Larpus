"""Optional pinned four-worker native pool; no runtime compilation or tuning."""
import ctypes
import threading
from pathlib import Path
from runtime.native_scoring import NativeScorer

def _huge_bytes(address,size):
 """Anonymous huge pages actually backing this mapping. An advisory request is not enough."""
 total=0;end=address+size;inside=False
 for line in Path('/proc/self/smaps').read_text().splitlines():
  parts=line.split()
  if not parts:continue
  head=parts[0]
  if head[0] in '0123456789abcdef' and '-' in head and all(c in '0123456789abcdef-' for c in head):
   start,stop=(int(x,16) for x in head.split('-',1));inside=start<end and stop>address
  elif inside and head=='AnonHugePages:':total+=int(parts[1])*1024
 return total

def _backing(address,nbytes):
 huge=2*1024*1024;reserved=(nbytes+huge-1)&~(huge-1);backed=_huge_bytes(address,reserved) if address else 0
 if not address or address%huge or backed<reserved:raise RuntimeError('Optimized matrix is not huge-page backed')
 return reserved,backed

class OptimizedScorer:
 _top=staticmethod(NativeScorer._top)
 def __init__(self,vectors):
  import numpy as np
  self.lock=threading.Lock();self.handle=None;self.matrix_bytes=0;self.reserved_bytes=0;self.huge_bytes=0
  self.library=NativeScorer._library('optimized-manifest.json','liblarpus_pool.so')
  if vectors.dtype!=np.float32 or vectors.ndim!=2 or vectors.shape[1]<1 or not np.isfinite(vectors).all():raise ValueError('Invalid vector matrix')
  half=np.ascontiguousarray(vectors,dtype=np.float16)
  self.shape=half.shape
  if not np.array_equal(half.astype(np.float32),vectors):raise ValueError('Index is not exact binary16 data')
  half.flags.writeable=False
  lib=self.library
  lib.lab_create.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t,ctypes.c_int,ctypes.c_int];lib.lab_create.restype=ctypes.c_void_p
  lib.lab_score.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];lib.lab_score.restype=ctypes.c_int
  lib.lab_destroy.argtypes=[ctypes.c_void_p];lib.lab_destroy.restype=None
  lib.lab_matrix.argtypes=[ctypes.c_void_p];lib.lab_matrix.restype=ctypes.c_void_p
  self.handle=lib.lab_create(half.ctypes.data,*self.shape,4,2)
  if not self.handle:raise RuntimeError('Optimized pool initialization failed')
  try:
   self.matrix_bytes=half.nbytes;self.reserved_bytes,self.huge_bytes=_backing(lib.lab_matrix(self.handle) or 0,half.nbytes)
   NativeScorer._check(self,vectors)
  except Exception:self.close();raise
 def close(self):
  with self.lock:
   if self.handle:self.library.lab_destroy(self.handle);self.handle=None
 def score(self,query):
  import numpy as np
  if query.dtype!=np.float32 or query.shape!=(self.shape[1],) or not query.flags.c_contiguous or not np.isfinite(query).all():raise ValueError('Invalid assembly query')
  with self.lock:
   if not self.handle:raise RuntimeError('Optimized scorer is closed')
   result=np.empty(self.shape[0],dtype=np.float32)
   if self.library.lab_score(self.handle,query.ctypes.data,result.ctypes.data) or not np.isfinite(result).all():raise RuntimeError('Optimized scoring failed')
   return result

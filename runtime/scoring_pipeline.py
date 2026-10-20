"""Station-wide scorer choice inside the serialized retrieval worker."""
import time
from runtime.native_scoring import NativeScorer
from runtime.optimized_scoring import OptimizedScorer
NAMES={'assembly-optimized':'Assembly optimized','assembly':'Assembly original','numpy':'NumPy'}
SCORER_RETRY_SECONDS=30.0
NUMPY_UNTIL='NumPy until the next scorer retry.'

class Pipeline:
 def __init__(self,vectors,preferred='assembly-optimized'):
  import numpy as np
  self.vectors=vectors;self.native=None;self.optimized=None;self.error=None;self._retry_at=None;self.requested=preferred;self.ambiguity_fallbacks=0;self.last_used=None
  if preferred not in NAMES:raise ValueError('Invalid preferred pipeline')
  self.max_norm=float(np.max(np.linalg.norm(vectors,axis=1))) if len(vectors) else 0
  # Exact duplicate rows have identical scores under either reduction order.
  packed=np.ascontiguousarray(vectors).view(np.dtype((np.void,vectors.shape[1]*vectors.dtype.itemsize))).reshape(-1)
  self.groups=np.unique(packed,return_inverse=True)[1]
  try:self.native=NativeScorer(vectors)
  except (OSError,ValueError,RuntimeError,ImportError,KeyError,AssertionError,AttributeError):
   if preferred=='assembly':self.error='Assembly unavailable or validation failed. '+NUMPY_UNTIL;self._retry_at=time.monotonic()+SCORER_RETRY_SECONDS
  try:self.optimized=OptimizedScorer(vectors)
  except (OSError,ValueError,RuntimeError,ImportError,KeyError,AssertionError,AttributeError):
   if preferred=='assembly-optimized':self.error='Optimized Assembly unavailable or validation failed. '+NUMPY_UNTIL;self._retry_at=time.monotonic()+SCORER_RETRY_SECONDS

 def _backend(self,identifier):
  return self.native if identifier=='assembly' else self.optimized if identifier=='assembly-optimized' else None

 def close(self):
  for backend in (self.native,self.optimized):
   close=getattr(backend,'close',None)
   if close:close()
  self.native=None;self.optimized=None

 def status(self):
  return {'active_id':self.requested if self._backend(self.requested) is not None else 'numpy',
          'requested_id':self.requested,'notice':self.error,'numpy_until':'retry-30s' if self.error else None,
          'workers':4,'last_used':self.last_used,'ambiguity_fallbacks':self.ambiguity_fallbacks,
          'pipelines':[{'id':key,'name':name,'available':key=='numpy' or self._backend(key) is not None} for key,name in NAMES.items()]}

 def select(self,identifier):
  self._consider_retry()
  if identifier not in NAMES or identifier!='numpy' and self._backend(identifier) is None:raise ValueError('Pipeline unavailable')
  self.requested=identifier
  self.last_used=None
  return self.status()

 def _ambiguous(self,scores,query,limit):
  import numpy as np
  count=min(max(1,limit)+1,len(scores))
  if count<2 or limit>=len(scores):return False
  indices=np.argpartition(scores,len(scores)-count)[-count:]
  margin=2e-6*self.max_norm*float(np.linalg.norm(query))
  if self.requested=='assembly-optimized':
   top=np.sort(scores[indices])
   # Identical vectors still represent distinct reference IDs at the cutoff.
   return bool(top[1]-top[0]<=margin)
  indices=indices[np.argsort(scores[indices],kind='stable')];top=scores[indices]
  # Owner-approved approximate ordering. This empirical tolerance is checked
  # at startup and in the benchmark, not a universal floating-point bound.
  # Only close distinct rows at the selected-set cutoff use NumPy.
  return bool(top[1]-top[0]<=margin and self.groups[indices[1]]!=self.groups[indices[0]])

 def _consider_retry(self):
  if self._retry_at is None or time.monotonic()<self._retry_at or self._backend(self.requested) is not None or self.requested=='numpy':return
  self._open(self.requested)

 def _open(self,identifier):
  try:backend=NativeScorer(self.vectors) if identifier=='assembly' else OptimizedScorer(self.vectors) if identifier=='assembly-optimized' else None
  except (OSError,ValueError,RuntimeError,ImportError,KeyError,AssertionError,AttributeError):
   self._retry_at=time.monotonic()+SCORER_RETRY_SECONDS;return
  if identifier=='assembly':self.native=backend
  elif identifier=='assembly-optimized':self.optimized=backend
  if backend is not None:self.error=None;self._retry_at=None

 def score(self,query,limit=18):
  self._consider_retry()
  backend=self._backend(self.requested)
  if backend is not None:
   try:
    scores=backend.score(query)
    if not self._ambiguous(scores,query,limit):self.last_used=self.requested;return scores
    self.ambiguity_fallbacks+=1
   except (OSError,ValueError,RuntimeError):
    close=getattr(backend,'close',None)
    if close:close()
    if self.requested=='assembly':self.native=None
    else:self.optimized=None
    self.error='Assembly scoring failed. '+NUMPY_UNTIL
    self._retry_at=time.monotonic()+SCORER_RETRY_SECONDS
  self.last_used='numpy'
  return self.vectors@query

"""Station-wide scorer choice inside the serialized retrieval worker."""
from runtime.native_scoring import NativeScorer
NAMES={'assembly':'Assembly pipeline','numpy':'NumPy'}

class Pipeline:
 def __init__(self,vectors):
  import numpy as np
  self.vectors=vectors;self.native=None;self.error=None;self.requested='assembly';self.ambiguity_fallbacks=0;self.last_used=None
  self.max_norm=float(np.max(np.linalg.norm(vectors,axis=1))) if len(vectors) else 0
  # Exact duplicate rows have identical scores under either reduction order.
  packed=np.ascontiguousarray(vectors).view(np.dtype((np.void,vectors.shape[1]*vectors.dtype.itemsize))).reshape(-1)
  self.groups=np.unique(packed,return_inverse=True)[1]
  try:self.native=NativeScorer(vectors)
  except (OSError,ValueError,RuntimeError,ImportError,KeyError,AssertionError):self.error='Assembly unavailable or validation failed; using NumPy.'

 def status(self):
  return {'active_id':'assembly' if self.requested=='assembly' and self.native is not None else 'numpy',
          'requested_id':self.requested,'notice':self.error,'workers':4,'last_used':self.last_used,'ambiguity_fallbacks':self.ambiguity_fallbacks,
          'pipelines':[{'id':key,'name':name,'available':key=='numpy' or self.native is not None} for key,name in NAMES.items()]}

 def select(self,identifier):
  if identifier not in NAMES or identifier=='assembly' and self.native is None:raise ValueError('Pipeline unavailable')
  self.requested=identifier
  self.last_used=None
  return self.status()

 def _ambiguous(self,scores,query,limit):
  import numpy as np
  count=min(max(1,limit)+1,len(scores))
  if count<2 or limit>=len(scores):return False
  indices=np.argpartition(scores,len(scores)-count)[-count:]
  indices=indices[np.argsort(scores[indices],kind='stable')];top=scores[indices]
  # Owner-approved approximate ordering. This empirical tolerance is checked
  # at startup and in the benchmark, not a universal floating-point bound.
  # Only close distinct rows at the selected-set cutoff use NumPy.
  margin=2e-6*self.max_norm*float(np.linalg.norm(query))
  return bool(top[1]-top[0]<=margin and self.groups[indices[1]]!=self.groups[indices[0]])

 def score(self,query,limit=18):
  if self.requested=='assembly' and self.native is not None:
   try:
    scores=self.native.score(query)
    if not self._ambiguous(scores,query,limit):self.last_used='assembly';return scores
    self.ambiguity_fallbacks+=1
   except (OSError,ValueError,RuntimeError):
    close=getattr(self.native,'close',None)
    if close:close()
    self.native=None;self.error='Assembly failed; using NumPy.'
  self.last_used='numpy'
  return self.vectors@query

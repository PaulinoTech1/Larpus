"""Stronger experiment-only cutoff check, including duplicate-row ties."""
import types

def apply_strict_guard(pipeline):
 def ambiguous(self,scores,query,limit):
  import numpy as np
  count=min(max(1,limit)+1,len(scores))
  if count<2 or limit>=len(scores):return False
  indices=np.argpartition(scores,len(scores)-count)[-count:]
  top=np.sort(scores[indices])
  margin=2e-6*self.max_norm*float(np.linalg.norm(query))
  # Even identical vector rows have distinct reference IDs. NumPy's exact
  # cutoff decision is retained rather than treating IDs as interchangeable.
  return bool(top[1]-top[0]<=margin)
 pipeline._ambiguous=types.MethodType(ambiguous,pipeline)

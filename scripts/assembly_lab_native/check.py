"""Numerical, ownership and boundary checks for the private C/assembly pool."""
import ctypes,json,sys
from pathlib import Path
import numpy as np

def library(path):
 lib=ctypes.CDLL(str(path))
 lib.lab_create.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_size_t,ctypes.c_int,ctypes.c_int];lib.lab_create.restype=ctypes.c_void_p
 lib.lab_score.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];lib.lab_score.restype=ctypes.c_int
 lib.lab_destroy.argtypes=[ctypes.c_void_p];lib.lab_destroy.restype=None
 lib.lab_matrix.argtypes=[ctypes.c_void_p];lib.lab_matrix.restype=ctypes.c_void_p
 return lib

def verify(lib):
 checks=0
 for mode in (0,1,2):
  for workers in (1,4,8):
   for rows,dim in ((0,1),(1,1),(3,7),(17,31),(31,33),(45,384),(23,385)):
    rng=np.random.default_rng(590019+rows+dim)
    half=rng.normal(size=(rows,dim)).astype('float16');matrix=half.astype('float32') if mode==1 else half
    handle=lib.lab_create(matrix.ctypes.data,rows,dim,workers,mode)
    assert handle,'Native pool create failed'
    saved=[]
    try:
     for _ in range(4):
      q=rng.normal(size=dim).astype('float32');q/=np.linalg.norm(q)
      output=np.full(rows+2,777,dtype='float32')
      assert lib.lab_score(handle,q.ctypes.data,output.ctypes.data+4)==0
      np.testing.assert_allclose(output[1:-1],half.astype('float32')@q,atol=2e-6,rtol=2e-5)
      assert output[0]==777 and output[-1]==777
      for a,b in saved:np.testing.assert_array_equal(a,b)
      saved.append((output,output.copy()));checks+=1
    finally:lib.lab_destroy(handle)
 assert not lib.lab_create(None,1,384,4,0)
 assert not lib.lab_create(None,0,0,4,0)
 assert not lib.lab_create(None,0,384,0,0)
 assert not lib.lab_create(None,0,384,21,0)
 assert lib.lab_score(None,None,None)==-1
 return checks

if __name__=='__main__':print(json.dumps({'native_checks':verify(library(Path(sys.argv[1])))}))

"""Owner benchmark snapshots only. Reads stock host/GPU state; changes nothing."""
import ctypes
from ctypes import wintypes
import math
import os
import shutil
import subprocess

class MemoryStatus(ctypes.Structure):
    _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD),
              ('total_physical',ctypes.c_ulonglong),('available_physical',ctypes.c_ulonglong),
              ('total_page',ctypes.c_ulonglong),('available_page',ctypes.c_ulonglong),
              ('total_virtual',ctypes.c_ulonglong),('available_virtual',ctypes.c_ulonglong),
              ('available_extended',ctypes.c_ulonglong)]

def cpu_counters():
    if os.name!='nt':return None
    idle,kernel,user=(wintypes.FILETIME() for _ in range(3))
    if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle),ctypes.byref(kernel),ctypes.byref(user)):return None
    return tuple((value.dwHighDateTime<<32)+value.dwLowDateTime for value in (idle,kernel,user))

def cpu_percent(before,after):
    if before is None or after is None:return None
    idle,kernel,user=(right-left for left,right in zip(before,after))
    total=kernel+user
    if min(idle,kernel,user)<0 or total<=0 or idle>total:return None
    return round(100*(total-idle)/total,3)

def host_memory():
    if os.name!='nt':return None
    status=MemoryStatus();status.length=ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):return None
    return {'total_bytes':status.total_physical,'available_bytes':status.available_physical}

def gpu_values(raw):
    names=('temperature_c','clock_mhz','power_w','power_limit_w','memory_total_mib','memory_used_mib','utilization_percent')
    try:values=[float(value.strip()) for value in raw.strip().split(',')]
    except (ValueError,TypeError):return None
    if len(values)!=len(names) or any(not math.isfinite(v) or v<0 for v in values):return None
    return dict(zip(names,values))

def gpu_snapshot():
    executable=shutil.which('nvidia-smi')
    if executable is None:return None
    fields='temperature.gpu,clocks.current.sm,power.draw,power.limit,memory.total,memory.used,utilization.gpu'
    result=subprocess.run([executable,'--id=0','--query-gpu='+fields,'--format=csv,noheader,nounits'],capture_output=True,timeout=5,check=True)
    if len(result.stdout)>1024:return None
    return gpu_values(result.stdout.decode('ascii'))

def snapshot():
    return {'cpu':read_optional(cpu_counters),'host_memory':read_optional(host_memory),'gpu':read_optional(gpu_snapshot)}

def read_optional(reader):
    try:return reader()
    except Exception:return None

def comparison(before,after,collection_seconds):
    return {'host_cpu_percent':cpu_percent(before['cpu'],after['cpu']),
            'host_memory_before':before['host_memory'],'host_memory_after':after['host_memory'],
            'gpu_before':before['gpu'],'gpu_after':after['gpu'],
            'collection_seconds':collection_seconds,
            'scope':'host counters and boundary GPU snapshots, not container attribution or CPU temperature'}

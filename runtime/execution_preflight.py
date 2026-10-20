"""Bounded fresh WSL acquisition. Isolation owns all approval/identity checks."""
import json
from runtime.isolation_probe import CODE

def observe(names,command,run) -> dict:
    result=run(command('python3','-c',CODE,json.dumps(names)),capture_output=True,timeout=75,check=True)
    if len(result.stdout)>8200000:raise ValueError('Oversized isolation snapshot')
    value=json.loads(result.stdout)
    if not isinstance(value,dict):raise ValueError('Invalid isolation observations')
    return value

"""Fixed local model identities and read-only broker selection state."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=Path('/run/larpus-selection/state.json')
PHASES={'ready','waiting','unloading','loading','verifying','restoring','failed'}
def catalog(root=ROOT):
 value=json.loads((root/'config/model-selection.json').read_text(encoding='utf8'))
 models=value['models']
 if value['version']!=1 or set(models)!={'larpus-3.5','larpus-3.8'}:raise ValueError('Unapproved model catalog')
 for entry in models.values():
  if not re.fullmatch(r'[a-z0-9.:-]+(?:_[A-Za-z0-9]+)*',entry['tag']) or not re.fullmatch('[a-f0-9]{64}',entry['weight_sha256']) or entry['context']!=131072:raise ValueError('Invalid model pin')
 return models
def model(identifier):
 if not isinstance(identifier,str) or identifier not in catalog():raise ValueError('Unknown local model')
 return catalog()[identifier]
def initial():
 return {'version':1,'active_id':'larpus-3.8','target_id':None,'phase':'ready','operation_id':None,'error':None}
def validate(value):
 if not isinstance(value,dict) or set(value)!=set(initial()) or value['version']!=1 or value['phase'] not in PHASES:raise ValueError('Invalid selection state')
 model(value['active_id'])
 if value['target_id'] is not None:model(value['target_id'])
 if value['operation_id'] is not None and not re.fullmatch('[a-f0-9]{32}',value['operation_id']):raise ValueError('Invalid selection operation')
 if value['error'] is not None and (not isinstance(value['error'],str) or len(value['error'])>160):raise ValueError('Invalid selection error')
 return value
def read_selection(path=None):
 path=STATE if path is None else Path(path)
 if path.is_symlink() or path.stat().st_size>4096:raise ValueError('Invalid selection file')
 return validate(json.loads(path.read_text(encoding='utf8')))
def is_switching(state):return state['phase']!='ready'

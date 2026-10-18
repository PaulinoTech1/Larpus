"""Authenticated gateway hooks; not part of the MCP tool surface."""
import threading
from runtime.model_switch import ModelSwitch
from runtime import model_selection
_LOCK=threading.Lock()
_CONTROLLER=None
def controller():
 global _CONTROLLER
 with _LOCK:
  if _CONTROLLER is None:_CONTROLLER=ModelSwitch()
  return _CONTROLLER
def status(handler,control=None):
 try:return handler.reply(200,(control or controller()).status())
 except (OSError,ValueError,RuntimeError):return handler.reply(503,{'error':'Local model controls are unavailable; chat selection is unchanged.'})
def switch(handler,control=None):
 try:
  body=handler.read_json(256)
  if not isinstance(body,dict) or set(body)!={'model_id'}:raise ValueError('Expected model ID')
  model_selection.model(body['model_id'])
  state=(control or controller()).request(body['model_id'])
  return handler.reply(200 if state['phase']=='ready' else 202,state)
 except (ValueError,TypeError):return handler.reply(400,{'error':'Choose one of the prepared local Larpus models.'})
 except RuntimeError as exc:return handler.reply(409,{'error':str(exc)[:160]})
 except OSError:return handler.reply(503,{'error':'Model control is unavailable. Selection unchanged.'})

def extra_get(handler,path):
 if path=='/api/retrieval-pipeline':
  from runtime.pipeline_routes import status as pipeline_status
  pipeline_status(handler);return True
 if path=='/api/model-selection':status(handler);return True
 if path=='/api/station-health':
  from runtime.health import read_latest
  handler.reply(200,read_latest());return True
 return False
def before_post(handler,drain):
 if drain.exists():handler.reply(503,{'error':'Finishing an update. Please retry shortly.'},{'Retry-After':'5'});return True
 if handler.path=='/api/model-selection':switch(handler);return True
 if handler.path=='/api/retrieval-pipeline':
  from runtime.pipeline_routes import select
  select(handler);return True
 return False

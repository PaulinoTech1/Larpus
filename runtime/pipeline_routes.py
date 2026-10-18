"""Authenticated owner controls; never exposed through the MCP tool surface."""
import json
import subprocess
from runtime import isolation
IDS=('assembly','numpy')
CODE="import json,sys;from runtime.retrieval_worker import call;request={'action':'pipeline'};request.update({'pipeline_id':sys.argv[1]} if len(sys.argv)>1 else {});print(json.dumps(call(request,8)))"

def control(identifier=None):
 profile=json.loads(isolation.PROFILE.read_text())
 args=['exec',isolation.agent_name(profile),'python','-c',CODE]
 if identifier is not None:
  if identifier not in IDS:raise ValueError('Invalid pipeline')
  args.append(identifier)
 result=isolation.query(*args)
 if not isinstance(result,dict) or result.get('active_id') not in IDS or result.get('requested_id') not in IDS:raise OSError('Pipeline unavailable')
 return result

def status(handler):
 try:return handler.reply(200,control())
 except (OSError,ValueError,KeyError,subprocess.SubprocessError):return handler.reply(503,{'error':'Retrieval pipeline controls are unavailable.'})

def select(handler):
 try:
  body=handler.read_json(256)
  if not isinstance(body,dict) or set(body)!={'pipeline_id'} or body['pipeline_id'] not in IDS:raise ValueError('Choose a pipeline')
 except (ValueError,TypeError):return handler.reply(400,{'error':'Choose Assembly pipeline or NumPy.'})
 try:return handler.reply(200,control(body['pipeline_id']))
 except (OSError,ValueError,KeyError,subprocess.SubprocessError):return handler.reply(503,{'error':'Pipeline switch failed. Check the current selection before retrying.'})

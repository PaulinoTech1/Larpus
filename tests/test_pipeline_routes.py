import unittest,re
from unittest.mock import patch
from runtime import pipeline_routes

class Handler:
 def __init__(self,body=None):self.body=body;self.result=None
 def read_json(self,limit):return self.body
 def reply(self,*args):self.result=args;return args

class PipelineRoutesTests(unittest.TestCase):
 def test_model_status_route_remains_callable_and_html_ids_are_unique(self):
  from runtime import model_routes
  from runtime.station_paths import ROOT
  h=Handler()
  with patch.object(model_routes,'status') as status:
   self.assertTrue(model_routes.extra_get(h,'/api/model-selection'));status.assert_called_once_with(h)
  ids=re.findall(r'\bid="([^"]+)"',(ROOT/'web/index.html').read_text(encoding='utf-8'))
  self.assertEqual(len(ids),len(set(ids)))
 def test_selection_only_accepts_predefined_pipeline(self):
  for body in ({'pipeline_id':'bad'},{'pipeline_id':'numpy','path':'x'},None):
   h=Handler(body)
   with patch.object(pipeline_routes,'control') as control:pipeline_routes.select(h)
   self.assertEqual(h.result[0],400);control.assert_not_called()
 def test_valid_control_and_unavailable_backend(self):
  h=Handler({'pipeline_id':'assembly'})
  with patch.object(pipeline_routes,'control',return_value={'active_id':'assembly'}):pipeline_routes.select(h)
  self.assertEqual(h.result,(200,{'active_id':'assembly'}))
  with patch.object(pipeline_routes,'control',side_effect=OSError()):pipeline_routes.select(h)
  self.assertEqual(h.result[0],503)

if __name__=='__main__':unittest.main()

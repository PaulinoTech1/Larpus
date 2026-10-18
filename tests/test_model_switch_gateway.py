import unittest
from unittest.mock import Mock,patch
from runtime import model_routes
class RoutesTests(unittest.TestCase):
 def handler(self,body):
  h=Mock();h.read_json.return_value=body;return h
 def test_exact_body_and_fixed_id_required(self):
  control=Mock()
  for body in ({'model_id':'other'},{'model_id':'larpus-3.8','command':'bad'},[],{'model_id':True}):
   h=self.handler(body);model_routes.switch(h,control);self.assertEqual(h.reply.call_args.args[0],400)
  control.request.assert_not_called()
 def test_async_request_and_busy_are_explicit(self):
  h=self.handler({'model_id':'larpus-3.8'});c=Mock();c.request.return_value={'phase':'loading'};model_routes.switch(h,c);self.assertEqual(h.reply.call_args.args[0],202)
  c.request.side_effect=RuntimeError('GPU notes maintenance is active');model_routes.switch(h,c);self.assertEqual(h.reply.call_args.args[0],409)

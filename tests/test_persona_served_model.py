"""Persona listings must name the model that actually answers chats."""
import json,threading,unittest
from types import SimpleNamespace
from unittest.mock import patch
from runtime import agents,inference,model_routes
from runtime.agents import load_personas,public_personas

class PersonaServedModelTests(unittest.TestCase):
    def test_public_view_prefers_served_tag_and_keeps_declared(self):
        current=load_personas()
        listed=public_personas(current,'larpus3.8:27b-q4')
        self.assertEqual({p['model'] for p in listed},{'larpus3.8:27b-q4'})
        self.assertEqual({p['model_source'] for p in listed},{'active-selection'})
        for p in listed:self.assertEqual(p['declared_model'],current[p['id']]['model'])
        fallback=public_personas(current,None)
        for p in fallback:
            self.assertEqual(p['model'],current[p['id']]['model'])
            self.assertEqual(p['model_source'],'persona-default')
        self.assertEqual(set(listed[0]),{'id','name','description','model','skills','declared_model','model_source'})

    def test_mcp_list_personas_uses_broker_active_model(self):
        with patch('runtime.inference.ollama',return_value={'models':[],'active_model':'larpus3.8:27b-q4'}):
            listed=inference.personas()
        self.assertEqual({p['model'] for p in listed['personas']},{'larpus3.8:27b-q4'})
        for bad in ({'models':[]},{'models':[],'active_model':'evil:latest'}):
            with patch('runtime.inference.ollama',return_value=bad):
                listed=inference.personas()
            self.assertEqual({p['model_source'] for p in listed['personas']},{'persona-default'})
        with patch('runtime.inference.ollama',side_effect=OSError('broker down')):
            listed=inference.personas()
        self.assertEqual({p['model_source'] for p in listed['personas']},{'persona-default'})

    def _control(self,state):
        control=SimpleNamespace(lock=threading.RLock(),state=state,refresh=lambda:None)
        return control

    def test_served_tag_follows_selection_and_fails_soft(self):
        ready={'version':1,'active_id':'larpus-3.8','target_id':None,'phase':'ready','operation_id':None,'error':None}
        self.assertEqual(model_routes.served_tag(self._control(ready)),'larpus3.8:27b-q4')
        self.assertEqual(model_routes.served_tag(self._control(dict(ready,active_id='larpus-3.5'))),'qwen3.5:27b-q4_K_M')
        self.assertIsNone(model_routes.served_tag(self._control(dict(ready,phase='loading',target_id='larpus-3.5'))))
        self.assertIsNone(model_routes.served_tag(self._control(dict(ready,active_id='unknown'))))
        broken=SimpleNamespace(lock=threading.RLock(),state=ready,refresh=lambda:(_ for _ in ()).throw(RuntimeError('wsl down')))
        self.assertIsNone(model_routes.served_tag(broken))
        with patch.object(model_routes,'controller',side_effect=OSError('no release')):
            self.assertIsNone(model_routes.served_tag())

if __name__=='__main__':unittest.main()

import dataclasses
import unittest
from runtime.execution_profiles import resolve,to_wire

class ExecutionProfilesTests(unittest.TestCase):
    def test_defaults_and_roundtrip(self):
        self.assertEqual((resolve().profile,resolve().interaction,resolve().base),('verified','conversation','verified'))
        for profile in ('verified','ultra-fast','diagnostic'):
            for interaction in ('conversation','analysis','coding'):
                context=resolve({'profile':profile,'interaction':interaction})
                self.assertEqual(resolve(to_wire(context)),context)
                with self.assertRaises(dataclasses.FrozenInstanceError):context.base='host'
        self.assertEqual(resolve({'profile':'diagnostic','base':'ultra-fast'}).base,'ultra-fast')
    def test_rejects_authority_and_invalid_shapes(self):
        for value in ([],True,'verified',{'profile':'raw'},{'profile':True},{'interaction':'tools'},{'base':'verified'},{'profile':'diagnostic','base':'diagnostic'},{'host':True},{'security':False},{'endpoint':'x'},{'profile':[]},{'interaction':None}):
            with self.subTest(value=value),self.assertRaises(ValueError):resolve(value)

import csv,datetime,io,unittest
from scripts.assembly_lab_metrics import summarize,qualify,correlate
from scripts.assembly_lab_sensors import parse_sample,Sensors
from scripts.assembly_lab_guard import apply_strict_guard

class LabMetricsTests(unittest.TestCase):
 def test_one_fast_sample_cannot_pass_repeated_target(self):
  values=[.5]+[1.4]*99
  stats=summarize(values)
  self.assertEqual(stats['at_or_below_1ms_fraction'],.01)
  self.assertFalse(qualify({'warm':stats},{'warm':summarize([2]*100)},True)['passed'])
 def test_each_condition_must_pass_and_correctness_is_required(self):
  good=summarize([.8]*100);slow=summarize([1.2]*100);baseline=summarize([2]*100)
  self.assertTrue(qualify({'warm':good},{'warm':baseline},True)['passed'])
  self.assertFalse(qualify({'warm':good,'pressure':slow},{'warm':baseline,'pressure':baseline},True)['passed'])
  self.assertFalse(qualify({'warm':good},{'warm':baseline},False)['passed'])
 def test_small_or_nonfinite_samples_are_not_evidence(self):
  with self.assertRaises(ValueError):summarize([float('nan')])
  self.assertFalse(qualify({'warm':summarize([.8]*3)},{'warm':summarize([2]*3)},True)['passed'])
 def test_sensor_join_uses_utc_and_excludes_other_work(self):
  samples=[{'utc':'2026-10-19T03:00:00+00:00','values':{'CPU PPT Limit [%]':'100'}},
           {'utc':'2026-10-19T03:00:05+00:00','values':{'CPU PPT Limit [%]':'70'}}]
  joined=correlate(samples,[{'phase':'warm','started_utc':'2026-10-19T03:00:04+00:00','finished_utc':'2026-10-19T03:00:06+00:00'}])
  self.assertEqual(joined[0]['samples'],1)
  self.assertEqual(joined[0]['sensors']['CPU PPT Limit [%]']['max'],70)

class SensorTests(unittest.TestCase):
 def test_local_time_and_duplicate_sensor_names_are_preserved(self):
  header=['Date','Time','CPU PPT [W]','CPU PPT [W]','Thermal Throttling (HTC) [Yes/No]']
  row=['18.10.2026','23:00:00.000','100','101','No']
  result=parse_sample(header,row,-240)
  self.assertEqual(result['utc'],'2026-10-19T03:00:00+00:00')
  self.assertEqual(result['values']['CPU PPT [W]'],'100')
  self.assertEqual(result['values']['CPU PPT [W] #2'],'101')
 def test_partial_or_repeated_header_is_rejected(self):
  h=['Date','Time','x']
  with self.assertRaises(ValueError):parse_sample(h,['18.10.2026','23:00:00.000'],-240)
  with self.assertRaises(ValueError):parse_sample(h,h,-240)
 def test_stale_thermal_or_raised_power_readings_stop_the_run(self):
  values={'CPU (Tctl/Tdie) [°C]':'65','CPU PPT [W]':'142','CPU PPT Limit [%]':'100',
   'Thermal Throttling (HTC) [Yes/No]':'No','Thermal Throttling (PROCHOT CPU) [Yes/No]':'No','Thermal Throttling (PROCHOT EXT) [Yes/No]':'No'}
  sample={'utc':'2026-10-19T03:00:00+00:00','values':values};sensor=object.__new__(Sensors)
  now=datetime.datetime.fromisoformat(sample['utc'])
  self.assertIsNone(sensor.safety(sample,now))
  self.assertIsNotNone(sensor.safety(sample,now+datetime.timedelta(seconds=16)))
  for key,value in [('CPU (Tctl/Tdie) [°C]','85'),('CPU PPT [W]','146'),('Thermal Throttling (HTC) [Yes/No]','Yes')]:
   altered={'utc':sample['utc'],'values':{**values,key:value}}
   self.assertIsNotNone(sensor.safety(altered,now))

class CandidateGuardTests(unittest.TestCase):
 def test_duplicate_rows_at_cutoff_fall_back_to_numpy(self):
  import numpy as np
  from runtime.scoring_pipeline import Pipeline
  p=object.__new__(Pipeline);p.requested='assembly';p.max_norm=1.;p.vectors=np.ones((20,1),dtype='float32')
  p.groups=np.zeros(20,dtype='int64');p.ambiguity_fallbacks=0;p._retry_at=None
  class Native:
   def score(self,q):return np.ones(20,dtype='float32')
  p.native=Native();apply_strict_guard(p)
  actual=p.score(np.ones(1,dtype='float32'),18)
  self.assertEqual(p.last_used,'numpy');self.assertEqual(p.ambiguity_fallbacks,1)
  np.testing.assert_array_equal(actual,p.vectors@np.ones(1,dtype='float32'))

if __name__=='__main__':unittest.main()

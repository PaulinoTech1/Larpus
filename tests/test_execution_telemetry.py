import unittest
from unittest.mock import patch
from scripts.execution_telemetry import cpu_percent, gpu_values


class ExecutionTelemetryTests(unittest.TestCase):
    def test_gpu_failure_preserves_host_observations(self):
        from scripts import execution_telemetry as telemetry
        with patch.object(telemetry,'cpu_counters',return_value=(1,2,3)),patch.object(telemetry,'host_memory',return_value={'total_bytes':64}),patch.object(telemetry,'gpu_snapshot',side_effect=OSError('unavailable')):
            result=telemetry.snapshot()
            self.assertEqual(result['cpu'],(1,2,3))
            self.assertEqual(result['host_memory'],{'total_bytes':64})
            self.assertIsNone(result['gpu'])
    def test_cpu_uses_host_counters_not_benchmark_process(self):
        self.assertEqual(cpu_percent((10,20,10),(15,30,20)),75.)
        self.assertIsNone(cpu_percent(None,(1,2,3)))
        self.assertIsNone(cpu_percent((10,20,10),(9,19,9)))

    def test_gpu_numeric_only_and_bounded(self):
        value=gpu_values('55, 1700, 210.5, 450, 24576, 20480, 90')
        self.assertEqual(value['temperature_c'],55.)
        self.assertEqual(value['power_limit_w'],450.)
        for text in ('N/A','1,2','private,1700,1,2,3,4,5','55, 1700, nan, 450, 24576, 20480, 90'):
            self.assertIsNone(gpu_values(text))

import unittest
from unittest import mock
import subprocess
import builtins
import os

import importlib.util
from pathlib import Path
import sys
import types

sys.modules['config'] = types.SimpleNamespace(use_availability=False, ext_sensors=False, version="0")

SRC_DIR = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import update

# Insert mocks for optional third party libraries so tests run without them
paho_module = types.ModuleType("paho")
paho_mqtt_module = types.ModuleType("paho.mqtt")
paho_client_module = types.ModuleType("paho.mqtt.client")
paho_mqtt_module.client = paho_client_module
paho_module.mqtt = paho_mqtt_module
sys.modules['paho'] = paho_module
sys.modules['paho.mqtt'] = paho_mqtt_module
sys.modules['paho.mqtt.client'] = paho_client_module
sys.modules['psutil'] = types.ModuleType("psutil")
sys.modules['requests'] = types.ModuleType("requests")

spec = importlib.util.spec_from_file_location("monitor", str(SRC_DIR / "rpi-cpu2mqtt.py"))
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

# Load ds18b20 module for testing
ds_spec = importlib.util.spec_from_file_location(
    "ds18b20", str(Path(__file__).parents[1] / "ext_sensor_lib" / "ds18b20.py")
)
ds18b20 = importlib.util.module_from_spec(ds_spec)
ds_spec.loader.exec_module(ds18b20)

class TestFunctions(unittest.TestCase):
    def test_check_sys_clock_speed(self):
        mock_data = '1500000\n'
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=mock_data)):
            self.assertEqual(monitor.check_sys_clock_speed(), 1500)

    def test_get_assignments(self):
        with open('tmp_config.py', 'w') as f:
            f.write('var1 = 1\nvar2 = "test"\n')
        try:
            result = update.get_assignments('tmp_config.py')
            self.assertEqual(result['var1'], 1)
            self.assertEqual(result['var2'], 'test')
        finally:
            os.remove('tmp_config.py')

    def test_check_git_version_remote(self):
        mock_completed = mock.Mock(stdout='v1.0\nv0.9\n', returncode=0)
        with mock.patch('subprocess.run', return_value=mock_completed) as m:
            version = update.check_git_version_remote('/tmp')
            self.assertEqual(version, 'v1.0')
            expected_calls = [
                mock.call([
                    'git', '-C', '/tmp', 'fetch', '--tags'
                ], check=True, stdout=mock.ANY, stderr=mock.ANY, text=True),
                mock.call([
                    'git', '-C', '/tmp', 'tag', '--sort=-v:refname'
                ], check=True, stdout=mock.ANY, stderr=mock.ANY, text=True)
            ]
            m.assert_has_calls(expected_calls)

    def test_install_requirements_error(self):
        with mock.patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cmd')):
            with self.assertRaises(SystemExit):
                update.install_requirements('/tmp')

    def test_sanitize_numeric(self):
        self.assertEqual(monitor.sanitize_numeric(10), 10)
        self.assertEqual(monitor.sanitize_numeric(None), 0)
        self.assertEqual(monitor.sanitize_numeric(float('nan')), 0)

    def test_check_wifi_signal(self):
        mock_run = mock.Mock()
        mock_run.stdout = 'wlan0 Quality=45/70 foo bar level=-60 dBm'
        with mock.patch('glob.glob', return_value=['/sys/class/ieee80211/phy0/device/net/wlan0']), \
             mock.patch('subprocess.run', return_value=mock_run):
            self.assertEqual(monitor.check_wifi_signal(''), 64)
            self.assertEqual(monitor.check_wifi_signal('dbm'), '-60')

    def test_check_uptime_timestamp(self):
        mock_date = mock.Mock(stdout='+0200\n')
        mock_uptime = mock.Mock(stdout='2024-01-01 12:34:56\n')
        with mock.patch('subprocess.run', side_effect=[mock_date, mock_uptime]):
            ts = monitor.check_uptime('timestamp')
            self.assertEqual(ts, '2024-01-01T12:34:56+0200')

    def test_check_uptime_seconds(self):
        mock_data = '12345.67 890.00\n'
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=mock_data)):
            self.assertEqual(monitor.check_uptime(''), 12345)

    def test_sensor_DS18B20(self):
        file_data = 'ignored\n00 00 00 00 00 00 00 00 00 t=21500\n'
        with mock.patch.object(builtins, 'open', mock.mock_open(read_data=file_data)):
            self.assertEqual(ds18b20.sensor_DS18B20('000000000000'), 21.5)

if __name__ == '__main__':
    unittest.main()


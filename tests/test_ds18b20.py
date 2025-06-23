import builtins
from unittest import mock

import sys
from pathlib import Path

SRC_DIR = Path(__file__).parents[1]
# Insert module path for ext_sensor_lib
sys.path.insert(0, str(SRC_DIR))

# import module
import ext_sensor_lib.ds18b20 as ds18b20


def test_sensor_ds18b20_reads_file():
    fake_data = "x\n" + " ".join(["0"] * 9 + ["t=23000"])
    with mock.patch.object(builtins, "open", mock.mock_open(read_data=fake_data)):
        assert ds18b20.sensor_DS18B20("0000") == 23.0


def test_get_available_sensors_filters_ids():
    with mock.patch.object(ds18b20.os, "listdir", return_value=["28-abc", "foo", "28-123"]):
        sensors = ds18b20.get_available_sensors()
    assert sensors == ["abc", "123"]

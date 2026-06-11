from pathlib import Path

import pytest

import storage
import detection

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_parse_detected_full_record_with_types():
    text = """
    {
      "computer_name": "  DET-PC  ",
      "os": "Ubuntu 24.04 LTS",
      "cpu": {"manufacturer": "AMD", "model": "Ryzen 5 5600X",
              "cores": "6", "threads": 12, "base_clock_ghz": "3.7"},
      "ram": {"capacity_gb": 32, "speed_mhz": 3200, "type": "DDR4"},
      "gpu": {"manufacturer": "NVIDIA", "model": "RTX 3060", "vram_gb": 12},
      "storage": [{"model": "980 Pro", "type": "NVMe SSD", "capacity": "1 TB"}],
      "motherboard": {"model": "B550-F"},
      "psu": {"model": "", "wattage": null}
    }
    """
    record = detection.parse_detected(text)

    assert record["computer_name"] == "DET-PC"          # trimmed
    assert record["os"] == "Ubuntu 24.04 LTS"
    assert record["cpu"]["model"] == "Ryzen 5 5600X"
    assert record["cpu"]["cores"] == 6                  # "6" -> int (integer field)
    assert record["cpu"]["threads"] == 12
    assert record["cpu"]["base_clock_ghz"] == 3.7       # "3.7" -> float (non-integer)
    assert record["ram"]["capacity_gb"] == 32
    assert record["gpu"]["vram_gb"] == 12
    assert record["storage"] == [{
        "manufacturer": "", "model": "980 Pro", "type": "NVMe SSD",
        "capacity": "1 TB", "form_factor": "",
    }]
    assert record["motherboard"]["model"] == "B550-F"
    assert record["psu"]["wattage"] is None


def test_parse_detected_sparse_fills_defaults():
    record = detection.parse_detected('{"computer_name": "X"}')
    expected = storage.empty_computer()
    expected["computer_name"] = "X"
    assert record == expected


def test_parse_detected_unparseable_number_defaults_to_none():
    record = detection.parse_detected('{"cpu": {"cores": "many"}}')
    assert record["cpu"]["cores"] is None


def test_parse_detected_ignores_unknown_keys():
    record = detection.parse_detected(
        '{"bogus": 1, "cpu": {"model": "i7", "made_up": "x"}}')
    assert record["cpu"]["model"] == "i7"
    assert "made_up" not in record["cpu"]
    assert "bogus" not in record


def test_parse_detected_non_string_top_level_is_ignored():
    record = detection.parse_detected('{"os": 11, "computer_name": "ok"}')
    assert record["os"] == ""                # number os ignored, stays blank
    assert record["computer_name"] == "ok"


def test_parse_detected_storage_accepts_single_object():
    # PowerShell's ConvertTo-Json renders a one-element array as a bare object.
    record = detection.parse_detected('{"storage": {"model": "solo"}}')
    assert record["storage"] == [{
        "manufacturer": "", "model": "solo", "type": "",
        "capacity": "", "form_factor": "",
    }]


def test_parse_detected_storage_skips_blank_and_non_dict_rows():
    text = '{"storage": [{"model": "keep"}, {}, "junk", {"model": ""}]}'
    record = detection.parse_detected(text)
    assert [d["model"] for d in record["storage"]] == ["keep"]


def test_parse_detected_storage_non_list_non_dict_ignored():
    record = detection.parse_detected('{"storage": 42}')
    assert record["storage"] == []


def test_parse_detected_invalid_json_raises():
    with pytest.raises(ValueError):
        detection.parse_detected("not json at all")


def test_parse_detected_non_object_raises():
    with pytest.raises(ValueError):
        detection.parse_detected("[1, 2, 3]")


def _assert_valid_detected_record(record: dict):
    assert record["computer_name"]
    assert record["os"]
    assert record["cpu"]["model"]
    assert isinstance(record["storage"], list) and record["storage"]
    # numbers came through as numbers (or None), never leftover strings
    assert record["cpu"]["cores"] is None or isinstance(record["cpu"]["cores"], int)


def test_windows_fixture_matches_contract():
    text = (FIXTURES / "detected-windows.json").read_text(encoding="utf-8")
    _assert_valid_detected_record(detection.parse_detected(text))

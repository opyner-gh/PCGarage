import storage
from components import widgets


def test_is_filled():
    assert widgets.is_filled("x") is True
    assert widgets.is_filled(0) is True            # zero is a real value
    assert widgets.is_filled("") is False
    assert widgets.is_filled(None) is False


def test_summarize_component_joins_present_fields():
    cpu = {"manufacturer": "AMD", "model": "Ryzen 5 5600X", "cores": 6,
           "threads": None, "base_clock_ghz": None, "boost_clock_ghz": None,
           "cooler": ""}
    text = widgets.summarize_component("cpu", cpu)
    assert "AMD" in text and "Ryzen 5 5600X" in text
    assert "None" not in text


def test_summary_row_columns_follow_schema():
    row = widgets.summary_row(storage.empty_computer())
    expected = (["Computer", "OS"]
                + [c["label"] for c in storage.SUMMARY_COMPONENTS]
                + ["Drives", "Created At"])
    assert list(row.keys()) == expected


def test_summary_row_has_one_line_per_component_and_drive_count():
    record = storage.empty_computer()
    record["computer_name"] = "RIG"
    record["created_at"] = "2026-01-01T00:00:00"
    record["os"] = "Windows 11"
    record["cpu"]["model"] = "Ryzen 5 5600X"
    record["storage"] = [{"model": "a"}, {"model": "b"}]

    row = widgets.summary_row(record)
    assert row["Computer"] == "RIG"
    assert row["OS"] == "Windows 11"
    assert row["Drives"] == 2
    assert "Ryzen 5 5600X" in row["CPU"]
    assert row["Created At"] == "2026-01-01T00:00:00"

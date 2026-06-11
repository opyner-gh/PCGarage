"""Smoke tests for the Streamlit pages via streamlit.testing AppTest.

These cannot assert pixels, but they execute the real page code paths (render,
collect widgets, save) and assert no uncaught exception — which is what catches
integration regressions like a navigation pathname collision or a KeyError on a
sparse record. Each test runs in an isolated temp working directory so the pages'
relative ``data/`` paths resolve there and the repo's real data is never touched.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import storage

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
INVENTORY_SCRIPT = "from components import inventory\ninventory.render()"
EDITOR_SCRIPT = "from components import editor\neditor.render()"

# A full record plus a deliberately sparse one (missing whole component keys and
# drives with empty select values) to exercise the defensive paths on both pages.
SAMPLE = [
    {
        "computer_name": "RIG-A", "created_at": "2026-01-01T00:00:00",
        "cpu": {"manufacturer": "AMD", "model": "5600X", "cores": 6, "threads": 12,
                "base_clock_ghz": 3.7, "boost_clock_ghz": 4.6, "cooler": "stock"},
        "ram": {"manufacturer": "Corsair", "capacity_gb": 32, "speed_mhz": 3600,
                "type": "DDR4", "configuration": "2 x 16GB"},
        "gpu": {"manufacturer": "NVIDIA", "model": "RTX 2070 Super", "vram_gb": 8,
                "brand": "EVGA"},
        "storage": [
            {"manufacturer": "Kingston", "model": "KC3000", "type": "NVMe SSD",
             "capacity": "1 TB", "form_factor": "M.2 2280"},
            {"manufacturer": "", "model": "old disk", "type": "", "capacity": "",
             "form_factor": ""},
        ],
        "motherboard": {"model": "B550-F", "form_factor": "ATX"},
        "psu": {"model": "EVGA 750 G5", "wattage": 750},
        "notes": "sim rig",
    },
    {"computer_name": "PARTIAL", "created_at": "2026-02-02T00:00:00", "storage": []},
]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Isolated CWD with a data/ dir; pages read/write data/ relative to here."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    return tmp_path


def _seed(workspace, records):
    storage.save_computers(records, path=workspace / "data" / "computers.json")


def _name_input(at):
    return next(t for t in at.text_input if t.label == "Computer Name *")


def test_app_boots_and_migrates_csv(workspace):
    (workspace / "data" / "computers.csv").write_text(
        "Computer Name,CPU,RAM,GPU,Storage,Motherboard,PSU,Notes,Created At\n"
        "OLD,intel,16gb,gtx 1060,crucial ssd,mobo,psu,note,2026-03-03T00:00:00\n",
        encoding="utf-8",
    )

    at = AppTest.from_file(APP_PATH).run()

    assert not at.exception
    assert (workspace / "data" / "computers.json").exists()
    assert (workspace / "data" / "computers.csv.bak").exists()
    assert not (workspace / "data" / "computers.csv").exists()


def test_inventory_renders_with_data(workspace):
    _seed(workspace, SAMPLE)

    at = AppTest.from_string(INVENTORY_SCRIPT).run()

    assert not at.exception
    assert any("Inventory" in title.value for title in at.title)


def test_inventory_empty_state(workspace):
    _seed(workspace, [])

    at = AppTest.from_string(INVENTORY_SCRIPT).run()

    assert not at.exception
    assert any("No computers saved" in info.value for info in at.info)


def test_editor_renders_add_mode(workspace):
    _seed(workspace, SAMPLE)

    at = AppTest.from_string(EDITOR_SCRIPT).run()

    assert not at.exception


def test_editor_renders_edit_mode_on_partial_record(workspace):
    _seed(workspace, SAMPLE)

    at = AppTest.from_string(EDITOR_SCRIPT).run()
    # Switch to edit mode; the selectbox defaults to the first record but the
    # sparse PARTIAL record must also be selectable without a KeyError.
    at.radio[0].set_value("Edit existing").run()
    at.selectbox[0].select(1).run()  # PARTIAL

    assert not at.exception


def _field_input_value(at, label):
    return next(t for t in at.text_input if t.label == label).value


def test_editor_edit_mode_prefills_selected_record(workspace):
    _seed(workspace, SAMPLE)

    at = AppTest.from_string(EDITOR_SCRIPT).run()
    at.radio[0].set_value("Edit existing").run()
    at.selectbox[0].select(0).run()  # RIG-A

    assert _field_input_value(at, "Computer Name *") == "RIG-A"
    # First "Model" text input belongs to the CPU component.
    assert _field_input_value(at, "Model") == "5600X"


def test_editor_switching_records_updates_form(workspace):
    _seed(workspace, SAMPLE)

    at = AppTest.from_string(EDITOR_SCRIPT).run()
    at.radio[0].set_value("Edit existing").run()
    at.selectbox[0].select(0).run()  # RIG-A
    assert _field_input_value(at, "Computer Name *") == "RIG-A"

    at.selectbox[0].select(1).run()  # PARTIAL
    assert _field_input_value(at, "Computer Name *") == "PARTIAL"


def test_editor_renders_drive_with_empty_select_values(workspace):
    # A drive whose type/form_factor are "" (migrated or newly added) must
    # render in the data_editor without error now that "" is a valid option.
    record = {
        **storage.empty_computer(), "computer_name": "DRV",
        "created_at": "2026-01-01T00:00:00",
        "storage": [{"manufacturer": "WD", "model": "Blue", "type": "",
                     "capacity": "2 TB", "form_factor": ""}],
    }
    _seed(workspace, [record])

    at = AppTest.from_string(EDITOR_SCRIPT).run()
    at.radio[0].set_value("Edit existing").run()
    at.selectbox[0].select(0).run()

    assert not at.exception


def test_editor_save_requires_name(workspace):
    _seed(workspace, [])

    at = AppTest.from_string(EDITOR_SCRIPT).run()
    at.button[0].click().run()  # Save with an empty name

    assert not at.exception
    assert any("required" in err.value.lower() for err in at.error)


def test_editor_add_saves_new_computer(workspace):
    _seed(workspace, [])

    at = AppTest.from_string(EDITOR_SCRIPT).run()
    _name_input(at).set_value("NEW-RIG").run()
    at.button[0].click().run()

    assert not at.exception
    saved = storage.load_computers(path=workspace / "data" / "computers.json")
    assert [c["computer_name"] for c in saved] == ["NEW-RIG"]
    assert saved[0]["created_at"]  # a fresh timestamp was stamped on add


def test_editor_edit_saves_and_preserves_created_at(workspace):
    _seed(workspace, SAMPLE)

    at = AppTest.from_string(EDITOR_SCRIPT).run()
    at.radio[0].set_value("Edit existing").run()
    at.selectbox[0].select(0).run()  # RIG-A
    _name_input(at).set_value("RIG-A-RENAMED").run()
    at.button[0].click().run()

    assert not at.exception
    saved = storage.load_computers(path=workspace / "data" / "computers.json")
    assert saved[0]["computer_name"] == "RIG-A-RENAMED"
    assert saved[0]["created_at"] == "2026-01-01T00:00:00"  # preserved, not restamped


@pytest.mark.parametrize("script", [INVENTORY_SCRIPT, EDITOR_SCRIPT])
def test_pages_handle_corrupt_json(workspace, script):
    (workspace / "data" / "computers.json").write_text("{ not valid json", encoding="utf-8")

    at = AppTest.from_string(script).run()

    assert not at.exception  # the page degrades gracefully instead of crashing
    assert any("Could not read" in err.value for err in at.error)


def test_inventory_renders_sparse_record(workspace):
    # Only the sparse record: exercises the "No details recorded" / "No drives
    # recorded" empty-state captions in the render helpers.
    _seed(workspace, [SAMPLE[1]])

    at = AppTest.from_string(INVENTORY_SCRIPT).run()

    assert not at.exception
    captions = [c.value for c in at.caption]
    assert any("No details recorded" in c for c in captions)
    assert any("No drives recorded" in c for c in captions)

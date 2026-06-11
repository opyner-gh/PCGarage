# Structured Component Specs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace PCGarage's flat-CSV computer tracker with a structured, optional-detail data model (per-component sub-fields, dynamic storage drives, icons), persisted as nested JSON, across two Streamlit pages (Inventory and Add / Edit).

**Architecture:** A pure-Python `storage.py` owns the schema, JSON load/save, and one-time CSV→JSON migration (unit-tested, no Streamlit import). Two thin page modules under `components/` render the Inventory (read-only) and Add / Edit pages, both reading the schema and helpers from `storage.py` and `components/widgets.py`. `app.py` only wires `st.navigation`.

**Tech Stack:** Python 3.12, Streamlit 1.58, pandas, pytest.

---

## File Structure

```
app.py                  # entry point: page config + st.navigation wiring only (rewritten)
storage.py              # schema constants, JSON load/save, CSV migration, record helpers (new)
components/
  __init__.py           # (new, empty)
  widgets.py            # shared render/format helpers, no page-level logic (new)
  inventory.py          # render the Inventory page (new)
  editor.py             # render the Add / Edit page (new)
tests/
  test_storage.py       # unit tests for storage.py (new)
requirements.txt        # add pytest (modified)
README.md               # update docs (modified)
data/computers.csv      # existing — migrated, then backed up to .bak by the app
```

Each task below is TDD where the code is pure logic (`storage.py`). The Streamlit
page modules cannot be meaningfully unit-tested, so their tasks are
"implement + manual verify by running the app".

---

## Task 1: Test tooling + project skeleton

**Files:**
- Modify: `requirements.txt`
- Create: `components/__init__.py` (empty)
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Add pytest to requirements**

Edit `requirements.txt` to read exactly:

```
streamlit
pandas
pytest
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: pytest installs successfully.

- [ ] **Step 3: Create empty package files**

Create `components/__init__.py` with no content.
Create `tests/__init__.py` with no content.

- [ ] **Step 4: Verify pytest runs**

Run: `pytest -q`
Expected: "no tests ran" (exit code 5) — confirms pytest is installed and discovers the `tests/` dir.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt components/__init__.py tests/__init__.py
git commit -m "chore: add pytest and package skeleton"
```

---

## Task 2: Schema constants and empty-record builder

**Files:**
- Create: `storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_storage.py`:

```python
import storage


def test_components_schema_has_expected_keys():
    keys = [c["key"] for c in storage.COMPONENTS]
    assert keys == ["cpu", "ram", "gpu", "storage", "motherboard", "psu"]


def test_every_component_has_label_icon_and_fields():
    for component in storage.COMPONENTS:
        assert component["label"]
        assert component["icon"]
        assert isinstance(component["fields"], list)
        for field in component["fields"]:
            assert field["key"]
            assert field["label"]
            assert field["widget"] in {"text", "number", "select"}
            if field["widget"] == "select":
                assert "" in field["options"]


def test_empty_computer_skeleton():
    record = storage.empty_computer()
    assert record["computer_name"] == ""
    assert record["created_at"] == ""
    assert record["notes"] == ""
    assert record["storage"] == []
    # scalar components are dicts with one entry per schema field
    assert record["cpu"]["model"] == ""
    assert record["cpu"]["cores"] is None          # number defaults to None
    assert record["motherboard"]["form_factor"] == ""
    assert record["psu"]["wattage"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'storage'`.

- [ ] **Step 3: Write minimal implementation**

Create `storage.py`:

```python
from __future__ import annotations

from pathlib import Path

DATA_DIR = Path("data")
JSON_PATH = DATA_DIR / "computers.json"
CSV_PATH = DATA_DIR / "computers.csv"

PAGE_ICONS = {"inventory": "📦", "editor": "✏️"}
COMPUTER_ICON = "🖥️"
NOTES_ICON = "📝"

# Single source of truth for every structured component and its fields.
# widget: "text" -> text_input, "number" -> number_input, "select" -> selectbox.
COMPONENTS = [
    {
        "key": "cpu",
        "label": "CPU",
        "icon": "🧠",
        "fields": [
            {"key": "manufacturer", "label": "Manufacturer", "widget": "select",
             "options": ["", "Intel", "AMD"]},
            {"key": "model", "label": "Model", "widget": "text"},
            {"key": "cores", "label": "Cores", "widget": "number"},
            {"key": "threads", "label": "Threads", "widget": "number"},
            {"key": "base_clock_ghz", "label": "Base Clock (GHz)", "widget": "number"},
            {"key": "boost_clock_ghz", "label": "Boost Clock (GHz)", "widget": "number"},
            {"key": "cooler", "label": "Cooler", "widget": "text"},
        ],
    },
    {
        "key": "ram",
        "label": "RAM",
        "icon": "🧩",
        "fields": [
            {"key": "manufacturer", "label": "Manufacturer", "widget": "text"},
            {"key": "capacity_gb", "label": "Capacity (GB)", "widget": "number"},
            {"key": "speed_mhz", "label": "Speed (MHz)", "widget": "number"},
            {"key": "type", "label": "Type", "widget": "select",
             "options": ["", "DDR3", "DDR4", "DDR5"]},
            {"key": "configuration", "label": "Configuration", "widget": "text"},
        ],
    },
    {
        "key": "gpu",
        "label": "GPU",
        "icon": "🎮",
        "fields": [
            {"key": "manufacturer", "label": "Manufacturer", "widget": "select",
             "options": ["", "NVIDIA", "AMD", "Intel"]},
            {"key": "model", "label": "Model", "widget": "text"},
            {"key": "vram_gb", "label": "VRAM (GB)", "widget": "number"},
            {"key": "brand", "label": "Brand (AIB)", "widget": "text"},
        ],
    },
    {
        "key": "storage",
        "label": "Storage",
        "icon": "💾",
        # storage is a dynamic list of drives; these are the per-drive fields.
        "fields": [
            {"key": "manufacturer", "label": "Manufacturer", "widget": "text"},
            {"key": "model", "label": "Model", "widget": "text"},
            {"key": "type", "label": "Type", "widget": "select",
             "options": ["", "NVMe SSD", "SATA SSD", "HDD"]},
            {"key": "capacity", "label": "Capacity", "widget": "text"},
            {"key": "form_factor", "label": "Form Factor", "widget": "select",
             "options": ["", "M.2 2280", "M.2 2230", "2.5\"", "3.5\""]},
        ],
    },
    {
        "key": "motherboard",
        "label": "Motherboard",
        "icon": "🔩",
        "fields": [
            {"key": "model", "label": "Model", "widget": "text"},
            {"key": "form_factor", "label": "Form Factor", "widget": "select",
             "options": ["", "ATX", "Micro-ATX", "Mini-ITX", "E-ATX"]},
        ],
    },
    {
        "key": "psu",
        "label": "PSU",
        "icon": "🔌",
        "fields": [
            {"key": "model", "label": "Model", "widget": "text"},
            {"key": "wattage", "label": "Wattage", "widget": "number"},
        ],
    },
]

SCALAR_COMPONENTS = [c for c in COMPONENTS if c["key"] != "storage"]
STORAGE_COMPONENT = next(c for c in COMPONENTS if c["key"] == "storage")


def _field_default(field: dict):
    return None if field["widget"] == "number" else ""


def empty_component(component: dict) -> dict:
    return {f["key"]: _field_default(f) for f in component["fields"]}


def empty_computer() -> dict:
    record = {"computer_name": "", "created_at": ""}
    for component in SCALAR_COMPONENTS:
        record[component["key"]] = empty_component(component)
    record["storage"] = []
    record["notes"] = ""
    return record
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add storage.py tests/test_storage.py
git commit -m "feat: add component schema and empty-record builder"
```

---

## Task 3: JSON load/save round-trip

**Files:**
- Modify: `storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_storage.py`:

```python
def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "computers.json"
    record = storage.empty_computer()
    record["computer_name"] = "TEST-RIG"
    record["cpu"]["model"] = "Ryzen 5 5600X"
    record["storage"] = [{"manufacturer": "Kingston", "model": "",
                          "type": "NVMe SSD", "capacity": "1 TB",
                          "form_factor": "M.2 2280"}]

    storage.save_computers([record], path=path)
    loaded = storage.load_computers(path=path)

    assert loaded == [record]


def test_load_missing_file_returns_empty_list(tmp_path):
    assert storage.load_computers(path=tmp_path / "nope.json") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -q`
Expected: FAIL — `AttributeError: module 'storage' has no attribute 'save_computers'`.

- [ ] **Step 3: Write minimal implementation**

Add to `storage.py` (add `import json` at the top with the other imports):

```python
import json


def load_computers(path: Path = JSON_PATH) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_computers(computers: list[dict], path: Path = JSON_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(computers, handle, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add storage.py tests/test_storage.py
git commit -m "feat: add JSON load and save"
```

---

## Task 4: Add and update record helpers

**Files:**
- Modify: `storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_storage.py`:

```python
def test_add_computer_appends(tmp_path):
    path = tmp_path / "computers.json"
    first = storage.empty_computer()
    first["computer_name"] = "A"
    second = storage.empty_computer()
    second["computer_name"] = "B"

    storage.add_computer(first, path=path)
    storage.add_computer(second, path=path)

    names = [c["computer_name"] for c in storage.load_computers(path=path)]
    assert names == ["A", "B"]


def test_update_computer_preserves_created_at(tmp_path):
    path = tmp_path / "computers.json"
    original = storage.empty_computer()
    original["computer_name"] = "A"
    original["created_at"] = "2026-01-01T00:00:00"
    storage.add_computer(original, path=path)

    edited = storage.empty_computer()
    edited["computer_name"] = "A-renamed"
    edited["created_at"] = "ignored"            # must be overwritten with original
    storage.update_computer(0, edited, path=path)

    result = storage.load_computers(path=path)[0]
    assert result["computer_name"] == "A-renamed"
    assert result["created_at"] == "2026-01-01T00:00:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -q`
Expected: FAIL — `AttributeError: module 'storage' has no attribute 'add_computer'`.

- [ ] **Step 3: Write minimal implementation**

Add to `storage.py`:

```python
def add_computer(computer: dict, path: Path = JSON_PATH) -> None:
    computers = load_computers(path=path)
    computers.append(computer)
    save_computers(computers, path=path)


def update_computer(index: int, computer: dict, path: Path = JSON_PATH) -> None:
    computers = load_computers(path=path)
    if not 0 <= index < len(computers):
        raise IndexError(f"Invalid computer index: {index}")
    computer = dict(computer)
    computer["created_at"] = computers[index].get("created_at", "")
    computers[index] = computer
    save_computers(computers, path=path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add storage.py tests/test_storage.py
git commit -m "feat: add and update computer record helpers"
```

---

## Task 5: CSV → JSON migration

**Files:**
- Modify: `storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_storage.py`:

```python
def _write_legacy_csv(path):
    path.write_text(
        "Computer Name,CPU,RAM,GPU,Storage,Motherboard,PSU,Notes,Created At\n"
        "XEON,intel xeon,64gb,quadro p4000,kingston nvme 500gb,"
        "dell precision 3630,stock,main workstation,2026-04-07T15:24:26\n"
        "TEXTRAM,cpu,dual channel,gpu,,mobo,psu,note,2026-04-07T16:00:00\n",
        encoding="utf-8",
    )


def test_migration_converts_rows(tmp_path):
    csv_path = tmp_path / "computers.csv"
    json_path = tmp_path / "computers.json"
    _write_legacy_csv(csv_path)

    storage.migrate_csv_if_present(json_path=json_path, csv_path=csv_path)

    computers = storage.load_computers(path=json_path)
    assert len(computers) == 2

    xeon = computers[0]
    assert xeon["computer_name"] == "XEON"
    assert xeon["created_at"] == "2026-04-07T15:24:26"
    assert xeon["cpu"]["model"] == "intel xeon"
    assert xeon["ram"]["capacity_gb"] == 64           # "64gb" parses to a number
    assert xeon["ram"]["configuration"] == ""
    assert xeon["gpu"]["model"] == "quadro p4000"
    assert xeon["storage"] == [{
        "manufacturer": "", "model": "kingston nvme 500gb",
        "type": "", "capacity": "", "form_factor": "",
    }]
    assert xeon["motherboard"]["model"] == "dell precision 3630"
    assert xeon["psu"]["model"] == "stock"
    assert xeon["notes"] == "main workstation"

    textram = computers[1]
    assert textram["ram"]["capacity_gb"] is None      # "dual channel" has no number
    assert textram["ram"]["configuration"] == "dual channel"
    assert textram["storage"] == []                   # blank storage -> no drives


def test_migration_is_noop_when_json_exists(tmp_path):
    csv_path = tmp_path / "computers.csv"
    json_path = tmp_path / "computers.json"
    _write_legacy_csv(csv_path)
    storage.save_computers([], path=json_path)        # JSON already present

    storage.migrate_csv_if_present(json_path=json_path, csv_path=csv_path)

    assert storage.load_computers(path=json_path) == []  # untouched


def test_migration_backs_up_csv(tmp_path):
    csv_path = tmp_path / "computers.csv"
    json_path = tmp_path / "computers.json"
    _write_legacy_csv(csv_path)

    storage.migrate_csv_if_present(json_path=json_path, csv_path=csv_path)

    assert not csv_path.exists()
    assert (tmp_path / "computers.csv.bak").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -q`
Expected: FAIL — `AttributeError: module 'storage' has no attribute 'migrate_csv_if_present'`.

- [ ] **Step 3: Write minimal implementation**

Add to `storage.py` (add `import csv` and `import re` at the top):

```python
import csv
import re


def _first_int(value: str):
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _row_to_computer(row: dict) -> dict:
    record = empty_computer()
    record["computer_name"] = (row.get("Computer Name") or "").strip()
    record["created_at"] = (row.get("Created At") or "").strip()
    record["cpu"]["model"] = (row.get("CPU") or "").strip()
    record["gpu"]["model"] = (row.get("GPU") or "").strip()
    record["motherboard"]["model"] = (row.get("Motherboard") or "").strip()
    record["psu"]["model"] = (row.get("PSU") or "").strip()
    record["notes"] = (row.get("Notes") or "").strip()

    ram = (row.get("RAM") or "").strip()
    capacity = _first_int(ram)
    if capacity is not None:
        record["ram"]["capacity_gb"] = capacity
    elif ram:
        record["ram"]["configuration"] = ram

    storage_value = (row.get("Storage") or "").strip()
    if storage_value:
        drive = empty_component(STORAGE_COMPONENT)
        drive["model"] = storage_value
        record["storage"] = [drive]

    return record


def migrate_csv_if_present(
    json_path: Path = JSON_PATH, csv_path: Path = CSV_PATH
) -> None:
    if json_path.exists():
        return
    if not csv_path.exists():
        return
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    computers = [_row_to_computer(row) for row in rows]
    save_computers(computers, path=json_path)
    csv_path.replace(csv_path.with_suffix(csv_path.suffix + ".bak"))
```

Note: `with_suffix(".csv" + ".bak")` would replace `.csv`; instead we append,
producing `computers.csv.bak`. `csv_path.with_suffix(csv_path.suffix + ".bak")`
on `computers.csv` yields `computers.csv.bak` because `.suffix` is `.csv`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -q`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git add storage.py tests/test_storage.py
git commit -m "feat: migrate legacy CSV to nested JSON"
```

---

## Task 6: Format/summary helpers

**Files:**
- Create: `components/widgets.py`
- Test: `tests/test_widgets.py`

These are pure string/format helpers (no Streamlit), so they are unit-tested.

- [ ] **Step 1: Write the failing test**

Create `tests/test_widgets.py`:

```python
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


def test_summary_row_has_one_line_per_component_and_drive_count():
    record = storage.empty_computer()
    record["computer_name"] = "RIG"
    record["created_at"] = "2026-01-01T00:00:00"
    record["cpu"]["model"] = "Ryzen 5 5600X"
    record["storage"] = [{"model": "a"}, {"model": "b"}]

    row = widgets.summary_row(record)
    assert row["Computer"] == "RIG"
    assert row["Drives"] == 2
    assert "Ryzen 5 5600X" in row["CPU"]
    assert row["Created At"] == "2026-01-01T00:00:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_widgets.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'components.widgets'`.

- [ ] **Step 3: Write minimal implementation**

Create `components/widgets.py`:

```python
from __future__ import annotations

import storage


def is_filled(value) -> bool:
    """True for any real value, including 0; False for None and empty string."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def _component_by_key(key: str) -> dict:
    return next(c for c in storage.COMPONENTS if c["key"] == key)


def summarize_component(key: str, data: dict) -> str:
    """One-line summary of a scalar component's filled fields, in schema order."""
    component = _component_by_key(key)
    parts = [str(data.get(f["key"])) for f in component["fields"]
             if is_filled(data.get(f["key"]))]
    return " · ".join(parts)


def summary_row(record: dict) -> dict:
    return {
        "Computer": record.get("computer_name", ""),
        "CPU": summarize_component("cpu", record.get("cpu", {})),
        "RAM": summarize_component("ram", record.get("ram", {})),
        "GPU": summarize_component("gpu", record.get("gpu", {})),
        "Drives": len(record.get("storage", [])),
        "Created At": record.get("created_at", ""),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_widgets.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add components/widgets.py tests/test_widgets.py
git commit -m "feat: add summary/format helpers for rendering"
```

---

## Task 7: Inventory page

**Files:**
- Create: `components/inventory.py`
- Modify: `components/widgets.py` (add a render helper used only by pages)

Streamlit rendering — verified by running the app, not unit tests.

- [ ] **Step 1: Add the detail-block render helper to `widgets.py`**

Append to `components/widgets.py` (add `import streamlit as st` at the top):

```python
import streamlit as st


def render_component_detail(component: dict, data: dict) -> None:
    """Render a scalar component's filled fields under an icon heading."""
    filled = [(f["label"], data.get(f["key"]))
              for f in component["fields"] if is_filled(data.get(f["key"]))]
    st.markdown(f"#### {component['icon']} {component['label']}")
    if not filled:
        st.caption("No details recorded.")
        return
    for label, value in filled:
        st.write(f"**{label}:** {value}")


def render_storage_detail(drives: list[dict]) -> None:
    component = _component_by_key("storage")
    st.markdown(f"#### {component['icon']} {component['label']}")
    if not drives:
        st.caption("No drives recorded.")
        return
    import pandas as pd
    columns = [f["key"] for f in component["fields"]]
    labels = {f["key"]: f["label"] for f in component["fields"]}
    frame = pd.DataFrame(drives).reindex(columns=columns).rename(columns=labels)
    st.dataframe(frame, width="stretch", hide_index=True)
```

- [ ] **Step 2: Create the Inventory page**

Create `components/inventory.py`:

```python
from __future__ import annotations

import pandas as pd
import streamlit as st

import storage
from components import widgets


def render() -> None:
    st.title(f"{storage.PAGE_ICONS['inventory']} Inventory")

    try:
        computers = storage.load_computers()
    except Exception as error:  # corrupt/unreadable JSON
        st.error(f"Could not read saved computers: {error}")
        computers = []

    if not computers:
        st.info("No computers saved yet. Use the Add / Edit page to create one.")
        return

    def label(index: int) -> str:
        record = computers[index]
        name = record.get("computer_name") or "Unnamed Computer"
        created = record.get("created_at") or ""
        return f"{name} ({created})" if created else name

    selected = st.selectbox(
        "Select a computer",
        options=list(range(len(computers))),
        format_func=label,
    )
    record = computers[selected]

    st.markdown(
        f"## {storage.COMPUTER_ICON} {record.get('computer_name') or 'Unnamed Computer'}"
    )

    left, right = st.columns(2)
    scalar = storage.SCALAR_COMPONENTS
    for offset, component in enumerate(scalar):
        target = left if offset % 2 == 0 else right
        with target:
            widgets.render_component_detail(component, record.get(component["key"], {}))

    widgets.render_storage_detail(record.get("storage", []))

    if storage.is_notes_present(record):
        st.markdown(f"#### {storage.NOTES_ICON} Notes")
        st.write(record["notes"])

    st.subheader("All Computers")
    table = pd.DataFrame([widgets.summary_row(c) for c in computers])
    st.dataframe(table, width="stretch", hide_index=True)
```

- [ ] **Step 3: Add the `is_notes_present` helper to `storage.py`**

Add to `storage.py`:

```python
def is_notes_present(record: dict) -> bool:
    return bool((record.get("notes") or "").strip())
```

- [ ] **Step 4: Manual verification (deferred)**

The page is rendered through `app.py` in Task 9; it cannot run standalone.
No command here — verification happens after navigation is wired.

- [ ] **Step 5: Commit**

```bash
git add components/inventory.py components/widgets.py storage.py
git commit -m "feat: add Inventory page and detail render helpers"
```

---

## Task 8: Add / Edit page

**Files:**
- Create: `components/editor.py`

This page uses plain widgets + a Save button (NOT `st.form`), because
`st.data_editor(num_rows="dynamic")` needs live reruns to add/remove drive rows,
which `st.form` suppresses. Values are read from each widget's return value on
the run where Save is clicked.

- [ ] **Step 1: Create the editor page**

Create `components/editor.py`:

```python
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import storage


def _field_input(component_key: str, field: dict, current):
    """Render one widget for a field; return its value (None/"" when empty)."""
    key = f"{component_key}_{field['key']}"
    label = field["label"]
    if field["widget"] == "number":
        value = None if current in (None, "") else current
        return st.number_input(label, value=value, step=1 if field["key"] in
                               {"cores", "threads", "capacity_gb", "speed_mhz",
                                "vram_gb", "wattage"} else None, key=key)
    if field["widget"] == "select":
        options = field["options"]
        index = options.index(current) if current in options else 0
        return st.selectbox(label, options=options, index=index, key=key)
    return st.text_input(label, value=current or "", key=key)


def _storage_editor(drives: list[dict]) -> list[dict]:
    component = storage.STORAGE_COMPONENT
    columns = [f["key"] for f in component["fields"]]
    labels = {f["key"]: f["label"] for f in component["fields"]}
    frame = pd.DataFrame(drives or [], columns=columns)

    column_config = {}
    for field in component["fields"]:
        if field["widget"] == "select":
            column_config[field["key"]] = st.column_config.SelectboxColumn(
                labels[field["key"]], options=[o for o in field["options"] if o])
        else:
            column_config[field["key"]] = st.column_config.TextColumn(
                labels[field["key"]])

    edited = st.data_editor(
        frame, num_rows="dynamic", width="stretch", hide_index=True,
        column_config=column_config, key="storage_editor",
    )
    records = edited.fillna("").to_dict("records")
    # Drop fully-empty rows the user added but left blank.
    return [r for r in records if any(str(v).strip() for v in r.values())]


def _collect(record: dict) -> dict:
    record["computer_name"] = st.session_state["computer_name_input"].strip()
    for component in storage.SCALAR_COMPONENTS:
        with st.expander(f"{component['icon']} {component['label']}"):
            for field in component["fields"]:
                record[component["key"]][field["key"]] = _field_input(
                    component["key"], field, record[component["key"]].get(field["key"]))
    with st.expander(f"{storage.STORAGE_COMPONENT['icon']} Storage", expanded=True):
        record["storage"] = _storage_editor(record.get("storage", []))
    record["notes"] = st.text_area(
        f"{storage.NOTES_ICON} Notes", value=record.get("notes", ""), key="notes_input")
    return record


def render() -> None:
    st.title(f"{storage.PAGE_ICONS['editor']} Add / Edit")

    try:
        computers = storage.load_computers()
    except Exception as error:
        st.error(f"Could not read saved computers: {error}")
        computers = []

    if computers:
        mode = st.radio("Mode", ["Add new", "Edit existing"], horizontal=True)
    else:
        mode = "Add new"
        st.info("Save at least one computer before you can edit.")

    edit_index = None
    if mode == "Edit existing" and computers:
        edit_index = st.selectbox(
            "Computer to edit",
            options=list(range(len(computers))),
            format_func=lambda i: computers[i].get("computer_name") or "Unnamed",
        )
        base = dict(computers[edit_index])
    else:
        base = storage.empty_computer()

    st.text_input("Computer Name *", value=base.get("computer_name", ""),
                  key="computer_name_input")

    record = _collect(base)

    if st.button("Save", type="primary"):
        if not record["computer_name"]:
            st.error("Computer Name is required.")
            return
        if mode == "Edit existing" and edit_index is not None:
            storage.update_computer(edit_index, record)
            st.success("Computer updated.")
        else:
            record["created_at"] = datetime.now().isoformat(timespec="seconds")
            storage.add_computer(record)
            st.success("Computer saved.")
        st.rerun()
```

- [ ] **Step 2: Manual verification (deferred)**

Rendered through `app.py` in Task 9; verified after navigation is wired.

- [ ] **Step 3: Commit**

```bash
git add components/editor.py
git commit -m "feat: add Add/Edit page with dynamic drive editor"
```

---

## Task 9: Navigation entry point + manual verification

**Files:**
- Modify: `app.py` (full rewrite)

- [ ] **Step 1: Rewrite `app.py`**

Replace the entire contents of `app.py` with:

```python
from __future__ import annotations

import streamlit as st

import storage
from components import inventory, editor


def main() -> None:
    st.set_page_config(page_title="PCGarage", layout="wide")
    storage.migrate_csv_if_present()

    pages = [
        st.Page(inventory.render, title="Inventory",
                icon=storage.PAGE_ICONS["inventory"], default=True),
        st.Page(editor.render, title="Add / Edit",
                icon=storage.PAGE_ICONS["editor"]),
    ]
    st.navigation(pages).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -q`
Expected: PASS (all tests from Tasks 2–6, 13 total).

- [ ] **Step 3: Launch the app and migrate real data**

Run: `streamlit run app.py`
Expected, by inspection in the browser:
- App starts with no errors; sidebar shows **📦 Inventory** and **✏️ Add / Edit**.
- `data/computers.json` now exists; `data/computers.csv` is renamed to
  `data/computers.csv.bak`.
- Inventory shows the two migrated machines (XEON, RYZEN-MASTER); only filled
  fields appear; the "All Computers" table shows one summary row each.

- [ ] **Step 4: Manually verify the Add / Edit flows**

In the running app:
- **Add:** create a new computer with a name, a couple of CPU/RAM fields, and two
  storage drives via the `+` row in the drives table. Save → it appears in
  Inventory with a fresh Created At.
- **Edit:** switch to "Edit existing", pick the new computer, change a field and
  delete one drive row. Save → changes persist and **Created At is unchanged**.
- **Validation:** try saving with an empty Computer Name → inline error, no write.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: wire two-page navigation and CSV migration on startup"
```

---

## Task 10: Update documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Replace the `## Features` and `## CSV Storage` sections of `README.md` so they
describe the new behavior:

```markdown
## Features

- Two pages: **Inventory** (browse saved computers) and **Add / Edit** (create or
  update entries)
- Structured, optional detail per component (manufacturer, RAM speed, clocks, etc.)
- Dynamic storage: add or remove as many drives per computer as the build needs
- Icons for every component
- Data saved as nested JSON; legacy `computers.csv` is migrated automatically on
  first run (and backed up to `computers.csv.bak`)

## Storage

Records are saved to `data/computers.json`. On first launch, any existing
`data/computers.csv` is converted to JSON and the original is preserved as
`data/computers.csv.bak`.
```

- [ ] **Step 2: Verify the app still runs**

Run: `pytest -q`
Expected: PASS (13 tests).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README for structured specs and JSON storage"
```

---

## Self-Review Notes

- **Spec coverage:** data model (Task 2), JSON persistence (Task 3), add/update
  with created_at preservation (Task 4), migration incl. RAM numeric branch +
  single-drive + backup + idempotency (Task 5), summary/flatten helpers (Task 6),
  Inventory page with filled-only fields + summary table (Task 7), Add/Edit with
  expanders + dynamic `data_editor` + required-name validation (Task 8),
  `st.navigation` two-page wiring + startup migration (Task 9), icons threaded
  through schema and pages (Tasks 2/7/8/9), tests on pure logic (Tasks 2–6), docs
  (Task 10). All spec sections map to a task.
- **Naming consistency:** `load_computers`, `save_computers`, `add_computer`,
  `update_computer`, `migrate_csv_if_present`, `empty_computer`, `empty_component`,
  `summarize_component`, `summary_row`, `is_filled`, `render_component_detail`,
  `render_storage_detail`, `is_notes_present` — each defined once and referenced
  consistently across tasks.
- **No placeholders:** every code step contains complete, runnable code.
```

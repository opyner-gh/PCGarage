# Auto-Detect PC Specs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user populate a computer record by running a per-platform detection script on a target PC and pasting its JSON output into a new Detect page, which normalizes it and pre-fills the Add / Edit form for review before saving.

**Architecture:** Standalone detection scripts (`scripts/detect-*.{ps1,sh}`) print one JSON object keyed to the app's record schema. A new pure-logic module `detection.py` defensively normalizes pasted JSON onto an `empty_computer()` skeleton. A new Streamlit page `components/detect.py` serves the scripts and imports pasted output, stashing the normalized record in `st.session_state["detected_draft"]` and switching to the editor, which consumes the draft as its Add-mode prefill.

**Tech Stack:** Python 3.12, Streamlit 1.58 (`st.navigation`/`st.Page`, `st.switch_page`, `st.download_button`, `st.text_area`, `st.session_state`), pandas, pytest, coverage, `streamlit.testing.v1.AppTest`. Detection scripts: PowerShell + CIM (Windows), bash + coreutils/lsblk/lspci/dmidecode (Linux), `system_profiler`/`sysctl` (macOS).

**Reference spec:** `docs/superpowers/specs/2026-06-11-auto-detect-specs-design.md`

## Conventions for every task

- Work on branch `feature/auto-detect-specs` (already checked out).
- TDD: write the failing test, run it red, implement, run it green, commit.
- Full suite + coverage after each code task:
  `python -m coverage run --source=. --omit="tests/*" -m pytest && python -m coverage report`
  Coverage must stay at **100%** (the only exempt line is one `# pragma: no cover`
  in Task 3, justified there).
- The `workspace` fixture in `tests/test_pages.py` chdirs to a temp dir; the
  Detect page resolves scripts relative to its own source (not the cwd), so page
  tests can run there and still read the real `scripts/` files.

## File Structure

| File | Responsibility | Task |
|------|----------------|------|
| `detection.py` *(new)* | Pure logic: `parse_detected(text) -> record` — JSON-parse, validate, normalize onto `empty_computer()` | 1 |
| `tests/test_detection.py` *(new)* | Unit tests for `parse_detected` + per-platform fixture contract tests | 1, 2, 6, 7 |
| `scripts/detect-windows.ps1` *(new)* | Windows detector (PowerShell + CIM) | 2 |
| `tests/fixtures/detected-windows.json` *(new)* | Representative Windows output | 2 |
| `storage.py` *(modify)* | Add `PAGE_ICONS["detect"]` | 3 |
| `components/detect.py` *(new)* | The 🔍 Detect page: script delivery + import box | 3 |
| `app.py` *(modify)* | Register the Detect page; expose pages via `session_state["_pages"]` | 3 |
| `components/editor.py` *(modify)* | Consume `session_state["detected_draft"]` as the Add-mode prefill | 4 |
| `README.md` *(modify)* | Document the Detect feature | 5 |
| `scripts/detect-linux.sh` *(new)* + fixture | Linux detector + fixture + contract test | 6 |
| `scripts/detect-macos.sh` *(new)* + fixture | macOS detector + fixture + contract test | 7 |

---

## Task 1: `detection.py` — parse + normalize (pure logic)

**Files:**
- Create: `detection.py`
- Test: `tests/test_detection.py`

`parse_detected` is the heart of the feature and has no Streamlit dependency, so
it is fully unit-tested. It starts from `storage.empty_computer()` and copies in
only what the pasted JSON provides, coercing number types per the schema and
dropping anything unknown.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_detection.py`:

```python
import pytest

import storage
import detection


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


def test_parse_detected_invalid_json_raises():
    with pytest.raises(ValueError):
        detection.parse_detected("not json at all")


def test_parse_detected_non_object_raises():
    with pytest.raises(ValueError):
        detection.parse_detected("[1, 2, 3]")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_detection.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'detection'`.

- [ ] **Step 3: Implement `detection.py`**

Create `detection.py`:

```python
from __future__ import annotations

import json

import storage


def _coerce_number(value, integer: bool):
    """Coerce a detected value to int/float per the field's schema flag.

    Returns None for blanks and anything that doesn't parse, so an undetectable
    or messy value lands as 'empty' rather than a wrong number or a crash.
    """
    if value is None or value == "":
        return None
    try:
        return int(value) if integer else float(value)
    except (TypeError, ValueError):
        return None


def _clean_str(value) -> str:
    return "" if value is None else str(value).strip()


def _normalize_drive(drive: dict) -> dict:
    keys = [f["key"] for f in storage.STORAGE_COMPONENT["fields"]]
    row = storage.empty_component(storage.STORAGE_COMPONENT)
    for key in keys:
        if key in drive:
            row[key] = _clean_str(drive[key])
    return row


def parse_detected(text: str) -> dict:
    """Parse a detection script's JSON output into a normalized computer record.

    Layers the pasted object onto a fresh ``storage.empty_computer()``: copies
    only known field keys per component, coerces numbers per the schema, accepts
    ``storage`` as a list (or a single object), drops unknown keys, and tolerates
    missing ones. Raises ValueError on invalid JSON or a non-object top level.
    """
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(f"not valid JSON ({error})") from error
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object describing one computer")

    record = storage.empty_computer()

    for key in ("computer_name", "os"):
        if isinstance(data.get(key), str):
            record[key] = data[key].strip()

    for component in storage.SCALAR_COMPONENTS:
        incoming = data.get(component["key"])
        if not isinstance(incoming, dict):
            continue
        for field in component["fields"]:
            if field["key"] not in incoming:
                continue
            value = incoming[field["key"]]
            if field["widget"] == "number":
                record[component["key"]][field["key"]] = _coerce_number(
                    value, field.get("integer", False))
            else:
                record[component["key"]][field["key"]] = _clean_str(value)

    drives = data.get(storage.STORAGE_COMPONENT["key"])
    if isinstance(drives, dict):                 # single drive -> one-item list
        drives = [drives]
    if isinstance(drives, list):
        normalized = []
        for drive in drives:
            if not isinstance(drive, dict):
                continue
            row = _normalize_drive(drive)
            if any(str(v).strip() for v in row.values()):
                normalized.append(row)
        record["storage"] = normalized

    return record
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_detection.py -q`
Expected: PASS (9 passed).

- [ ] **Step 5: Run the full suite + coverage**

Run: `python -m coverage run --source=. --omit="tests/*" -m pytest && python -m coverage report`
Expected: all pass; `detection.py` at 100%.

- [ ] **Step 6: Commit**

```bash
git add detection.py tests/test_detection.py
git commit -m "Add detection.parse_detected: normalize pasted detector JSON to a record"
```

---

## Task 2: Windows detection script + contract fixture

**Files:**
- Create: `scripts/detect-windows.ps1`
- Create: `tests/fixtures/detected-windows.json`
- Test: `tests/test_detection.py` (append one contract test)

The script can't run in CI (needs Windows + hardware). The CI guard is a
committed fixture representing its output, asserted to feed `parse_detected` to a
valid record. The user is on Windows and can run the script to validate it and
capture a real fixture.

- [ ] **Step 1: Write the failing contract test**

Append to `tests/test_detection.py`:

```python
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_detection.py::test_windows_fixture_matches_contract -q`
Expected: FAIL — `FileNotFoundError` (fixture absent).

- [ ] **Step 3: Create the fixture**

Create `tests/fixtures/detected-windows.json`:

```json
{
  "computer_name": "RYZEN-DESK",
  "os": "Microsoft Windows 11 Pro 10.0.22631",
  "cpu": {
    "manufacturer": "AMD",
    "model": "AMD Ryzen 7 5800X 8-Core Processor",
    "cores": 8,
    "threads": 16,
    "base_clock_ghz": 3.8,
    "boost_clock_ghz": null,
    "cooler": ""
  },
  "ram": {
    "manufacturer": "",
    "capacity_gb": 32,
    "speed_mhz": 3600,
    "type": "DDR4",
    "configuration": "2 modules"
  },
  "gpu": {
    "manufacturer": "NVIDIA",
    "model": "NVIDIA GeForce RTX 3070",
    "vram_gb": 8,
    "brand": ""
  },
  "storage": [
    {"manufacturer": "", "model": "Samsung SSD 980 PRO 1TB",
     "type": "NVMe SSD", "capacity": "931 GB", "form_factor": ""},
    {"manufacturer": "", "model": "ST2000DM008-2FR102",
     "type": "HDD", "capacity": "1863 GB", "form_factor": ""}
  ],
  "motherboard": {"model": "B550 AORUS ELITE", "form_factor": ""},
  "psu": {"model": "", "wattage": null}
}
```

- [ ] **Step 4: Create the Windows script**

Create `scripts/detect-windows.ps1`:

```powershell
#requires -Version 5.0
<#
  PCGarage hardware detector (Windows).
  Prints a JSON object describing this machine to stdout, and writes a copy to
  pcgarage-detected.json next to this script. Progress/warnings go to stderr so
  stdout stays clean JSON you can paste straight into PCGarage's Detect page.

  Run from PowerShell:
    powershell -ExecutionPolicy Bypass -File .\detect-windows.ps1
#>
$ErrorActionPreference = 'SilentlyContinue'

function ConvertTo-GB([double]$bytes) { [int][math]::Round($bytes / 1GB) }

# ---- CPU ----
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cpuManufacturer = ''
if ($cpu.Manufacturer -match 'Intel')                  { $cpuManufacturer = 'Intel' }
elseif ($cpu.Manufacturer -match 'AMD|Advanced Micro') { $cpuManufacturer = 'AMD' }
$baseClockGhz = $null
if ($cpu.MaxClockSpeed) { $baseClockGhz = [math]::Round($cpu.MaxClockSpeed / 1000.0, 2) }

# ---- RAM ----
$mem = @(Get-CimInstance Win32_PhysicalMemory)
$capacityGb = $null; $speedMhz = $null; $ramType = ''; $ramConfig = ''
if ($mem.Count -gt 0) {
    $sum = ($mem | Measure-Object -Property Capacity -Sum).Sum
    if ($sum) { $capacityGb = ConvertTo-GB $sum }
    if ($mem[0].Speed) { $speedMhz = [int]$mem[0].Speed }
    $ddr = @{ '20' = 'DDR3'; '21' = 'DDR3'; '24' = 'DDR3'; '26' = 'DDR4'; '34' = 'DDR5' }
    $ramType = [string]$ddr["$($mem[0].SMBIOSMemoryType)"]
    if ($mem.Count -gt 1) { $ramConfig = "$($mem.Count) modules" }
}

# ---- GPU ----
$gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1
$gpuManufacturer = ''
if ($gpu.Name -match 'NVIDIA|GeForce|RTX|GTX|Quadro') { $gpuManufacturer = 'NVIDIA' }
elseif ($gpu.Name -match 'Radeon|AMD')                { $gpuManufacturer = 'AMD' }
elseif ($gpu.Name -match 'Intel')                     { $gpuManufacturer = 'Intel' }
# AdapterRAM is a signed 32-bit value that lies for cards over 4 GB; prefer the
# registry's qwMemorySize and only fall back to AdapterRAM.
$vramGb = $null
$qwKey = 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000'
$qw = (Get-ItemProperty -Path $qwKey -Name 'HardwareInformation.qwMemorySize').'HardwareInformation.qwMemorySize'
if ($qw -gt 0)                 { $vramGb = ConvertTo-GB $qw }
elseif ($gpu.AdapterRAM -gt 0) { $vramGb = ConvertTo-GB $gpu.AdapterRAM }

# ---- Storage ----
$drives = @()
foreach ($disk in Get-CimInstance Win32_DiskDrive) {
    $type = ''
    if ($disk.MediaType -match 'Fixed hard disk') { $type = 'HDD' }
    if ($disk.Model -match 'NVMe' -or $disk.InterfaceType -match 'NVMe') { $type = 'NVMe SSD' }
    $capacity = ''
    if ($disk.Size) { $capacity = "$(ConvertTo-GB $disk.Size) GB" }
    $drives += [ordered]@{
        manufacturer = ''
        model        = [string]$disk.Model
        type         = $type
        capacity     = $capacity
        form_factor  = ''
    }
}

# ---- Motherboard / OS / host ----
$board  = Get-CimInstance Win32_BaseBoard | Select-Object -First 1
$os     = Get-CimInstance Win32_OperatingSystem
$osName = ("{0} {1}" -f $os.Caption, $os.Version).Trim()

$record = [ordered]@{
    computer_name = $env:COMPUTERNAME
    os            = $osName
    cpu = [ordered]@{
        manufacturer    = $cpuManufacturer
        model           = [string]$cpu.Name
        cores           = [int]$cpu.NumberOfCores
        threads         = [int]$cpu.NumberOfLogicalProcessors
        base_clock_ghz  = $baseClockGhz
        boost_clock_ghz = $null
        cooler          = ''
    }
    ram = [ordered]@{
        manufacturer  = ''
        capacity_gb   = $capacityGb
        speed_mhz     = $speedMhz
        type          = $ramType
        configuration = $ramConfig
    }
    gpu = [ordered]@{
        manufacturer = $gpuManufacturer
        model        = [string]$gpu.Name
        vram_gb      = $vramGb
        brand        = ''
    }
    storage = $drives
    motherboard = [ordered]@{ model = [string]$board.Product; form_factor = '' }
    psu         = [ordered]@{ model = ''; wattage = $null }
}

$json = $record | ConvertTo-Json -Depth 5
Write-Output $json

$dest = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'pcgarage-detected.json'
Set-Content -Path $dest -Value $json -Encoding UTF8
[Console]::Error.WriteLine("PCGarage: detected specs also written to $dest")
```

- [ ] **Step 5: (Recommended, on Windows) validate the script and refresh the fixture**

Run in a real PowerShell window:
`powershell -ExecutionPolicy Bypass -File .\scripts\detect-windows.ps1 > real.json`
Open `real.json`, sanity-check the values, and if they look good replace
`tests/fixtures/detected-windows.json` with this real output (keep it
representative — two drives, populated CPU/RAM/GPU). If you can't run Windows
right now, keep the hand-written fixture; it already matches the contract.

- [ ] **Step 6: Run the contract test + full suite**

Run: `python -m pytest tests/test_detection.py -q`
Expected: PASS (10 passed).
Run: `python -m coverage run --source=. --omit="tests/*" -m pytest && python -m coverage report`
Expected: all pass; coverage 100% (scripts aren't Python-measured).

- [ ] **Step 7: Commit**

```bash
git add scripts/detect-windows.ps1 tests/fixtures/detected-windows.json tests/test_detection.py
git commit -m "Add Windows detection script and its contract fixture"
```

---

## Task 3: Detect page + navigation wiring

**Files:**
- Modify: `storage.py` (PAGE_ICONS)
- Create: `components/detect.py`
- Modify: `app.py` (register page + expose pages registry)
- Test: `tests/test_pages.py` (append Detect page tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pages.py`:

```python
DETECT_SCRIPT = "from components import detect\ndetect.render()"


def test_detect_page_renders(workspace):
    at = AppTest.from_string(DETECT_SCRIPT).run()
    assert not at.exception
    assert any("Detect" in t.value for t in at.title)


def test_detect_empty_paste_shows_error(workspace):
    at = AppTest.from_string(DETECT_SCRIPT).run()
    at.button[0].click().run()
    assert not at.exception
    assert any("Paste" in e.value for e in at.error)


def test_detect_invalid_json_shows_error(workspace):
    at = AppTest.from_string(DETECT_SCRIPT).run()
    at.text_area[0].set_value("not json").run()
    at.button[0].click().run()
    assert not at.exception
    assert any("Couldn't read" in e.value for e in at.error)


def test_detect_valid_paste_stashes_draft(workspace):
    at = AppTest.from_string(DETECT_SCRIPT).run()
    at.text_area[0].set_value(
        '{"computer_name": "DET-PC", "cpu": {"model": "i7"}}').run()
    at.button[0].click().run()
    assert not at.exception
    # No _pages registry in the isolated page test, so it falls back to a success
    # message and leaves the draft for the editor to pick up.
    assert at.session_state["detected_draft"]["computer_name"] == "DET-PC"
    assert any("Add / Edit" in s.value for s in at.success)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_pages.py -k detect -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'components.detect'`.

- [ ] **Step 3: Add the page icon in `storage.py`**

In `storage.py`, change the `PAGE_ICONS` line:

```python
PAGE_ICONS = {"inventory": "📦", "editor": "✏️"}
```

to:

```python
PAGE_ICONS = {"inventory": "📦", "editor": "✏️", "detect": "🔍"}
```

- [ ] **Step 4: Create `components/detect.py`**

```python
from __future__ import annotations

from pathlib import Path

import streamlit as st

import storage
import detection

# Detection scripts are source, not user data — resolve them relative to this
# package so the page works regardless of the process's working directory.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"

# Platforms grow as their scripts land (Linux in Task 6, macOS in Task 7).
PLATFORMS = {
    "Windows": {
        "file": "detect-windows.ps1",
        "lang": "powershell",
        "run": "powershell -ExecutionPolicy Bypass -File .\\detect-windows.ps1",
    },
}


def render() -> None:
    st.title(f"{storage.PAGE_ICONS['detect']} Detect")
    st.write(
        "Run a detection script on the target PC, then paste its JSON output "
        "below to pre-fill a new computer for review.")

    platform = st.selectbox("Platform", options=list(PLATFORMS))
    spec = PLATFORMS[platform]
    script_text = (SCRIPTS_DIR / spec["file"]).read_text(encoding="utf-8")

    st.markdown(
        f"1. Download or copy **{spec['file']}** and run it on the target PC:\n\n"
        f"   ```\n   {spec['run']}\n   ```\n"
        "2. Copy the JSON it prints (a `pcgarage-detected.json` copy is also "
        "saved next to the script).\n"
        "3. Paste it below and click **Load into editor**.")
    st.download_button(f"⬇️ Download {spec['file']}", data=script_text,
                       file_name=spec["file"])
    with st.expander("Or copy the script"):
        st.code(script_text, language=spec["lang"])

    st.divider()
    pasted = st.text_area("Paste the script's JSON output here", height=220,
                          key="detect_paste")
    if st.button("Load into editor", type="primary"):
        if not pasted.strip():
            st.error("Paste the detection output first.")
            return
        try:
            record = detection.parse_detected(pasted)
        except ValueError as error:
            st.error(f"Couldn't read that detection output: {error}")
            return
        st.session_state["detected_draft"] = record
        pages = st.session_state.get("_pages")
        if pages:
            st.switch_page(pages["editor"])  # pragma: no cover (AppTest can't drive callable-page nav)
        else:
            st.success("Loaded. Open the **Add / Edit** page to review and save.")
```

- [ ] **Step 5: Register the page in `app.py`**

Replace the body of `main()` in `app.py`. Current:

```python
    pages = [
        st.Page(inventory.render, title="Inventory", url_path="inventory",
                icon=storage.PAGE_ICONS["inventory"], default=True),
        st.Page(editor.render, title="Add / Edit", url_path="add-edit",
                icon=storage.PAGE_ICONS["editor"]),
    ]
    st.navigation(pages).run()
```

New:

```python
    pages = {
        "inventory": st.Page(inventory.render, title="Inventory",
                             url_path="inventory",
                             icon=storage.PAGE_ICONS["inventory"], default=True),
        "editor": st.Page(editor.render, title="Add / Edit", url_path="add-edit",
                          icon=storage.PAGE_ICONS["editor"]),
        "detect": st.Page(detect.render, title="Detect", url_path="detect",
                          icon=storage.PAGE_ICONS["detect"]),
    }
    # Expose the Page objects so a page can switch to another (Detect -> editor).
    # st.switch_page needs the StreamlitPage object for callable-defined pages.
    st.session_state["_pages"] = pages
    st.navigation(list(pages.values())).run()
```

And update the import line at the top of `app.py`:

```python
from components import inventory, editor
```

to:

```python
from components import inventory, editor, detect
```

- [ ] **Step 6: Run the Detect tests, then the full suite**

Run: `python -m pytest tests/test_pages.py -k detect -q`
Expected: PASS (4 passed).
Run: `python -m coverage run --source=. --omit="tests/*" -m pytest && python -m coverage report`
Expected: all pass; coverage 100% (the single `st.switch_page` line is
`# pragma: no cover`).

- [ ] **Step 7: Commit**

```bash
git add storage.py components/detect.py app.py tests/test_pages.py
git commit -m "Add Detect page: serve scripts, import pasted output, hand off to editor"
```

---

## Task 4: Editor consumes the detected draft

**Files:**
- Modify: `components/editor.py`
- Test: `tests/test_pages.py` (append)

The editor turns a handed-off `session_state["detected_draft"]` into an Add-mode
prefill by staging it under `editor_draft`, forcing Add mode, and bumping the
existing `editor_nonce` so the form widgets rebuild with the detected values. The
draft clears on save (the existing nonce-bump reset path) so the next Add starts
blank.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pages.py`:

```python
def test_editor_prefills_from_detected_draft(workspace):
    _seed(workspace, [])
    draft = {**storage.empty_computer(),
             "computer_name": "DETECTED-PC", "os": "Ubuntu 24.04"}
    draft["cpu"]["model"] = "Core i7-12700"

    at = AppTest.from_string(EDITOR_SCRIPT)
    at.session_state["detected_draft"] = draft
    at.run()

    assert not at.exception
    assert _name_input(at).value == "DETECTED-PC"
    assert _os_input(at).value == "Ubuntu 24.04"
    assert _field_input_value(at, "Model") == "Core i7-12700"   # CPU model prefilled
    assert "detected_draft" not in at.session_state             # one-shot, consumed


def test_editor_saves_detected_draft_then_resets(workspace):
    _seed(workspace, [])
    draft = {**storage.empty_computer(), "computer_name": "DET", "os": "Win 11"}

    at = AppTest.from_string(EDITOR_SCRIPT)
    at.session_state["detected_draft"] = draft
    at.run()
    at.button[0].click().run()

    assert not at.exception
    saved = storage.load_computers(path=workspace / "data" / "computers.json")
    assert saved[0]["computer_name"] == "DET"
    assert saved[0]["os"] == "Win 11"
    assert "editor_draft" not in at.session_state   # cleared after save
    assert _name_input(at).value == ""              # form reset for next entry
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_pages.py -k detected_draft -q`
Expected: FAIL — `_name_input(at).value` is `""`, not `"DETECTED-PC"` (draft
not consumed yet).

- [ ] **Step 3: Implement draft consumption in `components/editor.py`**

(a) Add the consume call + helper. Change `render()`. Current:

```python
def render() -> None:
    st.title(f"{storage.PAGE_ICONS['editor']} Add / Edit")

    try:
        computers = storage.load_computers()
```

New:

```python
def render() -> None:
    st.title(f"{storage.PAGE_ICONS['editor']} Add / Edit")

    _consume_detected_draft()

    try:
        computers = storage.load_computers()
```

(b) Add the helper just below `render()` (before `_editor_form`):

```python
def _consume_detected_draft() -> None:
    """If the Detect page handed off a freshly detected record, stage it as the
    Add-mode prefill and bump the nonce so the form rebuilds with those values.
    One-shot: the inbound key is popped so later edits aren't overwritten."""
    draft = st.session_state.pop("detected_draft", None)
    if draft is None:
        return
    st.session_state["editor_draft"] = draft
    st.session_state["editor_mode"] = "Add new"
    st.session_state["editor_nonce"] = st.session_state.get("editor_nonce", 0) + 1
```

(c) Give the mode radio a key so the consume step can force Add mode. Current:

```python
        editing = st.radio(
            "Mode", ["Add new", "Edit existing"], horizontal=True) == "Edit existing"
```

New:

```python
        editing = st.radio(
            "Mode", ["Add new", "Edit existing"], horizontal=True,
            key="editor_mode") == "Edit existing"
```

(d) Use the staged draft as the Add-mode base. Current:

```python
    if edit_index is not None:
        # Layer the stored record onto a complete skeleton so missing
        # component keys never KeyError, and deepcopy so editing does not
        # mutate the loaded list in place.
        base = storage.empty_computer()
        base.update(copy.deepcopy(computers[edit_index]))
    else:
        base = storage.empty_computer()
```

New:

```python
    if edit_index is not None:
        # Layer the stored record onto a complete skeleton so missing
        # component keys never KeyError, and deepcopy so editing does not
        # mutate the loaded list in place.
        base = storage.empty_computer()
        base.update(copy.deepcopy(computers[edit_index]))
    else:
        base = storage.empty_computer()
        draft = st.session_state.get("editor_draft")
        if draft is not None:
            base.update(copy.deepcopy(draft))
```

(e) Clear the draft on a successful save. Current (end of the Save handler):

```python
        # Bump the nonce so the form re-renders with fresh, empty widgets.
        st.session_state["editor_nonce"] = nonce + 1
        st.rerun()
```

New:

```python
        # Bump the nonce so the form re-renders with fresh, empty widgets, and
        # drop any detected draft so the next Add starts blank.
        st.session_state.pop("editor_draft", None)
        st.session_state["editor_nonce"] = nonce + 1
        st.rerun()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_pages.py -k detected_draft -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full suite + coverage**

Run: `python -m coverage run --source=. --omit="tests/*" -m pytest && python -m coverage report`
Expected: all pass; coverage 100%.

- [ ] **Step 6: Commit**

```bash
git add components/editor.py tests/test_pages.py
git commit -m "Pre-fill the editor from a detected draft handed off by the Detect page"
```

---

## Task 5: Document the Detect feature

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a feature bullet.** After the line:

```markdown
- Track each machine's **installed operating system** and free-form notes.
```

add:

```markdown
- **Auto-detect** a machine's specs: run a detection script (Windows / Linux /
  macOS) on the target PC and paste its output to pre-fill a new computer.
```

- [ ] **Step 2: Add a usage section.** After the "## Where your data lives"
section, insert:

```markdown
## Auto-detecting specs

Open the **🔍 Detect** page, pick the target machine's platform, and download (or
copy) the detection script:

- **Windows:** `scripts/detect-windows.ps1` — `powershell -ExecutionPolicy Bypass -File .\detect-windows.ps1`
- **Linux:** `scripts/detect-linux.sh` — `bash detect-linux.sh` (run with `sudo` for RAM speed/type and board model)
- **macOS:** `scripts/detect-macos.sh` — `bash detect-macos.sh`

Run it on the target PC, copy the JSON it prints (also saved as
`pcgarage-detected.json`), paste it into the Detect page, and click **Load into
editor**. The Add / Edit form opens pre-filled for review. Some fields can't be
detected — **PSU model/wattage** never, and GPU VRAM / form factors are
best-effort — so review and fill those in before saving.
```

- [ ] **Step 3: Add project-layout rows.** After the `requirements-dev.txt` row
in the Project-layout table, add:

```markdown
| `components/detect.py` | The Detect page (script delivery + import) |
| `detection.py` | Parse + normalize pasted detector output (no Streamlit) |
| `scripts/` | Per-platform hardware detection scripts |
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "Document the auto-detect feature in the README"
```

---

## Task 6: Linux detection script + contract fixture

**Files:**
- Create: `scripts/detect-linux.sh`
- Create: `tests/fixtures/detected-linux.json`
- Modify: `components/detect.py` (add Linux to `PLATFORMS`)
- Test: `tests/test_detection.py` (append contract test)

- [ ] **Step 1: Write the failing contract test**

Append to `tests/test_detection.py`:

```python
def test_linux_fixture_matches_contract():
    text = (FIXTURES / "detected-linux.json").read_text(encoding="utf-8")
    _assert_valid_detected_record(detection.parse_detected(text))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_detection.py::test_linux_fixture_matches_contract -q`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Create the fixture**

Create `tests/fixtures/detected-linux.json`:

```json
{
  "computer_name": "ubuntu-box",
  "os": "Ubuntu 24.04.1 LTS",
  "cpu": {
    "manufacturer": "Intel",
    "model": "Intel(R) Core(TM) i5-10400 CPU @ 2.90GHz",
    "cores": 6, "threads": 12, "base_clock_ghz": 4.3,
    "boost_clock_ghz": null, "cooler": ""
  },
  "ram": {
    "manufacturer": "", "capacity_gb": 16, "speed_mhz": 2666,
    "type": "DDR4", "configuration": "2 modules"
  },
  "gpu": {
    "manufacturer": "NVIDIA",
    "model": "NVIDIA Corporation GA106 [GeForce RTX 3060]",
    "vram_gb": null, "brand": ""
  },
  "storage": [
    {"manufacturer": "", "model": "Samsung SSD 870 EVO 500GB",
     "type": "SATA SSD", "capacity": "465.8G", "form_factor": ""}
  ],
  "motherboard": {"model": "PRIME B460M-A", "form_factor": ""},
  "psu": {"model": "", "wattage": null}
}
```

- [ ] **Step 4: Create the Linux script**

Create `scripts/detect-linux.sh`:

```bash
#!/usr/bin/env bash
# PCGarage hardware detector (Linux). Prints a JSON object to stdout and writes a
# copy to pcgarage-detected.json beside the script. Warnings go to stderr. RAM
# speed/type and the board model need root via dmidecode; without it those stay
# blank.  Run:  bash detect-linux.sh   (or: sudo bash detect-linux.sh)
set -u
warn() { echo "PCGarage: $*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }
# Minimal JSON string escaper (covers backslash, quote, newline, tab).
esc() { printf '%s' "${1-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' \
        -e ':a;N;$!ba;s/\n/\\n/g;s/\t/\\t/g'; }
# Emit a JSON value: a bare number when the arg is an integer, else null.
num() { case "${1-}" in ''|*[!0-9]*) printf 'null';; *) printf '%s' "$1";; esac; }

# ---- CPU ----
cpu_model=""; cpu_cores=""; cpu_threads=""; cpu_base="null"; cpu_vendor=""
if have lscpu; then
  lscpu_out=$(lscpu)
  cpu_model=$(printf '%s\n' "$lscpu_out" | sed -n 's/^Model name:[[:space:]]*//p' | head -1)
  cps=$(printf '%s\n' "$lscpu_out" | sed -n 's/^Core(s) per socket:[[:space:]]*//p' | head -1)
  sockets=$(printf '%s\n' "$lscpu_out" | sed -n 's/^Socket(s):[[:space:]]*//p' | head -1)
  if [ -n "${cps:-}" ] && [ -n "${sockets:-}" ]; then cpu_cores=$((cps * sockets)); fi
  cpu_threads=$(nproc 2>/dev/null)
  maxmhz=$(printf '%s\n' "$lscpu_out" | sed -n 's/^CPU max MHz:[[:space:]]*//p' | head -1)
  if [ -n "${maxmhz:-}" ]; then cpu_base=$(awk "BEGIN{printf \"%.2f\", $maxmhz/1000}"); fi
fi
case "$cpu_model" in *Intel*) cpu_vendor=Intel;; *AMD*) cpu_vendor=AMD;; esac

# ---- RAM ----
ram_gb=""; ram_speed=""; ram_type=""; ram_config=""
memkb=$(awk '/^MemTotal:/{print $2}' /proc/meminfo 2>/dev/null)
if [ -n "${memkb:-}" ]; then ram_gb=$(awk "BEGIN{printf \"%d\", ($memkb/1048576)+0.5}"); fi
if have dmidecode; then
  dmi=$(dmidecode -t memory 2>/dev/null)
  if [ -n "$dmi" ]; then
    ram_speed=$(printf '%s\n' "$dmi" | sed -n 's/^[[:space:]]*Speed:[[:space:]]*\([0-9]\{1,\}\).*/\1/p' | head -1)
    ram_type=$(printf '%s\n' "$dmi" | sed -n 's/^[[:space:]]*Type:[[:space:]]*\(DDR[0-9]\).*/\1/p' | head -1)
    mods=$(printf '%s\n' "$dmi" | grep -cE '^[[:space:]]*Size:[[:space:]]*[0-9]+ (M|G)B')
    if [ "${mods:-0}" -gt 1 ]; then ram_config="$mods modules"; fi
  else warn "dmidecode returned nothing; run with sudo for RAM speed/type"; fi
else warn "dmidecode not found; RAM speed/type left blank"; fi

# ---- GPU ----
gpu_model=""; gpu_vendor=""
if have lspci; then
  gpu_line=$(lspci 2>/dev/null | grep -iE 'vga compatible controller|3d controller' | head -1)
  gpu_model=$(printf '%s' "$gpu_line" | sed 's/^[^:]*: //')
  case "$gpu_line" in
    *NVIDIA*) gpu_vendor=NVIDIA;;
    *AMD*|*Radeon*|*"Advanced Micro"*) gpu_vendor=AMD;;
    *Intel*) gpu_vendor=Intel;;
  esac
else warn "lspci not found; GPU left blank"; fi

# ---- Storage (physical disks) ----
drives=""
if have lsblk; then
  while IFS= read -r line; do
    eval "$line"   # lsblk -P emits NAME="..." MODEL="..." SIZE="..." ROTA="..." TRAN="..."
    t="SATA SSD"; [ "${ROTA:-0}" = "1" ] && t="HDD"; [ "${TRAN:-}" = "nvme" ] && t="NVMe SSD"
    row=$(printf '{"manufacturer":"","model":"%s","type":"%s","capacity":"%s","form_factor":""}' \
          "$(esc "${MODEL:-}")" "$t" "$(esc "${SIZE:-}")")
    drives="${drives:+$drives,}$row"
  done < <(lsblk -dn -o NAME,MODEL,SIZE,ROTA,TRAN -P 2>/dev/null)
else warn "lsblk not found; storage left empty"; fi

# ---- Motherboard / OS / host ----
board=""
if have dmidecode; then board=$(dmidecode -s baseboard-product-name 2>/dev/null | head -1); fi
os_name=""
if [ -r /etc/os-release ]; then os_name=$(. /etc/os-release; printf '%s' "${PRETTY_NAME:-}"); fi
host=$(hostname 2>/dev/null)

json=$(cat <<EOF
{
  "computer_name": "$(esc "$host")",
  "os": "$(esc "$os_name")",
  "cpu": {"manufacturer": "$(esc "$cpu_vendor")", "model": "$(esc "$cpu_model")",
          "cores": $(num "$cpu_cores"), "threads": $(num "$cpu_threads"),
          "base_clock_ghz": ${cpu_base:-null}, "boost_clock_ghz": null, "cooler": ""},
  "ram": {"manufacturer": "", "capacity_gb": $(num "$ram_gb"),
          "speed_mhz": $(num "$ram_speed"), "type": "$(esc "$ram_type")",
          "configuration": "$(esc "$ram_config")"},
  "gpu": {"manufacturer": "$(esc "$gpu_vendor")", "model": "$(esc "$gpu_model")",
          "vram_gb": null, "brand": ""},
  "storage": [${drives}],
  "motherboard": {"model": "$(esc "$board")", "form_factor": ""},
  "psu": {"model": "", "wattage": null}
}
EOF
)
printf '%s\n' "$json"
dest="$(cd "$(dirname "$0")" && pwd)/pcgarage-detected.json"
printf '%s\n' "$json" > "$dest"
warn "detected specs also written to $dest"
```

- [ ] **Step 5: Add Linux to the page's `PLATFORMS`**

In `components/detect.py`, extend `PLATFORMS`:

```python
PLATFORMS = {
    "Windows": {
        "file": "detect-windows.ps1",
        "lang": "powershell",
        "run": "powershell -ExecutionPolicy Bypass -File .\\detect-windows.ps1",
    },
    "Linux": {
        "file": "detect-linux.sh",
        "lang": "bash",
        "run": "bash detect-linux.sh   # sudo for RAM speed/type + board model",
    },
}
```

- [ ] **Step 6: (Recommended, on Linux) validate + refresh the fixture**

Run `bash scripts/detect-linux.sh > real.json` (and `sudo bash ...` to compare),
verify the JSON parses and the values look right, and if so replace
`tests/fixtures/detected-linux.json` with the real output. If you can't run Linux
now, keep the hand-written fixture.

- [ ] **Step 7: Run the contract test + full suite**

Run: `python -m pytest tests/test_detection.py -q`
Expected: PASS.
Run: `python -m coverage run --source=. --omit="tests/*" -m pytest && python -m coverage report`
Expected: all pass; coverage 100%.

- [ ] **Step 8: Commit**

```bash
git add scripts/detect-linux.sh tests/fixtures/detected-linux.json components/detect.py tests/test_detection.py
git commit -m "Add Linux detection script, fixture, and Detect-page entry"
```

---

## Task 7: macOS detection script + contract fixture

**Files:**
- Create: `scripts/detect-macos.sh`
- Create: `tests/fixtures/detected-macos.json`
- Modify: `components/detect.py` (add macOS to `PLATFORMS`)
- Test: `tests/test_detection.py` (append contract test)

- [ ] **Step 1: Write the failing contract test**

Append to `tests/test_detection.py`:

```python
def test_macos_fixture_matches_contract():
    text = (FIXTURES / "detected-macos.json").read_text(encoding="utf-8")
    _assert_valid_detected_record(detection.parse_detected(text))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_detection.py::test_macos_fixture_matches_contract -q`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Create the fixture**

Create `tests/fixtures/detected-macos.json`:

```json
{
  "computer_name": "Johns-Mac-mini",
  "os": "macOS 14.5",
  "cpu": {
    "manufacturer": "", "model": "Apple M2", "cores": 8, "threads": 8,
    "base_clock_ghz": null, "boost_clock_ghz": null, "cooler": ""
  },
  "ram": {
    "manufacturer": "", "capacity_gb": 16, "speed_mhz": null,
    "type": "", "configuration": ""
  },
  "gpu": {"manufacturer": "Apple", "model": "Apple M2", "vram_gb": null, "brand": ""},
  "storage": [
    {"manufacturer": "", "model": "APPLE SSD AP0512Z", "type": "NVMe SSD",
     "capacity": "500.28 GB", "form_factor": ""}
  ],
  "motherboard": {"model": "", "form_factor": ""},
  "psu": {"model": "", "wattage": null}
}
```

- [ ] **Step 4: Create the macOS script**

Create `scripts/detect-macos.sh`:

```bash
#!/bin/bash
# PCGarage hardware detector (macOS). Prints a JSON object to stdout and writes a
# copy to pcgarage-detected.json beside the script. Warnings go to stderr.
# Run:  bash detect-macos.sh
set -u
warn() { echo "PCGarage: $*" >&2; }
esc()  { printf '%s' "${1-}" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' \
         -e ':a;N;$!ba;s/\n/\\n/g;s/\t/\\t/g'; }
num()  { case "${1-}" in ''|*[!0-9]*) printf 'null';; *) printf '%s' "$1";; esac; }

host=$(scutil --get ComputerName 2>/dev/null || hostname)
os_name="macOS $(sw_vers -productVersion 2>/dev/null)"

cpu_model=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
cpu_cores=$(sysctl -n hw.physicalcpu 2>/dev/null)
cpu_threads=$(sysctl -n hw.logicalcpu 2>/dev/null)

mem_bytes=$(sysctl -n hw.memsize 2>/dev/null)
ram_gb=""
if [ -n "${mem_bytes:-}" ]; then ram_gb=$(awk "BEGIN{printf \"%d\", ($mem_bytes/1073741824)+0.5}"); fi

# GPU via system_profiler text (Chipset Model line).
gpu_model=$(system_profiler SPDisplaysDataType 2>/dev/null \
            | sed -n 's/^[[:space:]]*Chipset Model:[[:space:]]*//p' | head -1)
gpu_vendor=""
case "$gpu_model" in
  *Apple*) gpu_vendor=Apple;; *AMD*|*Radeon*) gpu_vendor=AMD;;
  *NVIDIA*) gpu_vendor=NVIDIA;; *Intel*) gpu_vendor=Intel;;
esac

# Storage: physical NVMe/SATA media, name + size.
drives=""
sp_storage=$(system_profiler SPNVMeDataType SPSerialATADataType 2>/dev/null)
while IFS= read -r model; do
  [ -n "$model" ] || continue
  row=$(printf '{"manufacturer":"","model":"%s","type":"NVMe SSD","capacity":"","form_factor":""}' "$(esc "$model")")
  drives="${drives:+$drives,}$row"
done < <(printf '%s\n' "$sp_storage" | sed -n 's/^[[:space:]]*Model:[[:space:]]*//p')

json=$(cat <<EOF
{
  "computer_name": "$(esc "$host")",
  "os": "$(esc "$os_name")",
  "cpu": {"manufacturer": "", "model": "$(esc "$cpu_model")",
          "cores": $(num "$cpu_cores"), "threads": $(num "$cpu_threads"),
          "base_clock_ghz": null, "boost_clock_ghz": null, "cooler": ""},
  "ram": {"manufacturer": "", "capacity_gb": $(num "$ram_gb"),
          "speed_mhz": null, "type": "", "configuration": ""},
  "gpu": {"manufacturer": "$(esc "$gpu_vendor")", "model": "$(esc "$gpu_model")",
          "vram_gb": null, "brand": ""},
  "storage": [${drives}],
  "motherboard": {"model": "", "form_factor": ""},
  "psu": {"model": "", "wattage": null}
}
EOF
)
printf '%s\n' "$json"
dest="$(cd "$(dirname "$0")" && pwd)/pcgarage-detected.json"
printf '%s\n' "$json" > "$dest"
warn "detected specs also written to $dest"
```

- [ ] **Step 5: Add macOS to the page's `PLATFORMS`**

In `components/detect.py`, add to `PLATFORMS`:

```python
    "macOS": {
        "file": "detect-macos.sh",
        "lang": "bash",
        "run": "bash detect-macos.sh",
    },
```

- [ ] **Step 6: (Recommended, on macOS) validate + refresh the fixture**

Run `bash scripts/detect-macos.sh > real.json`, confirm it parses and the values
are sensible, and replace `tests/fixtures/detected-macos.json` with the real
output if so. Otherwise keep the hand-written fixture.

- [ ] **Step 7: Run the contract test + full suite**

Run: `python -m pytest tests/test_detection.py -q`
Expected: PASS.
Run: `python -m coverage run --source=. --omit="tests/*" -m pytest && python -m coverage report`
Expected: all pass; coverage 100%.

- [ ] **Step 8: Commit**

```bash
git add scripts/detect-macos.sh tests/fixtures/detected-macos.json components/detect.py tests/test_detection.py
git commit -m "Add macOS detection script, fixture, and Detect-page entry"
```

---

## Final verification (after all tasks)

- [ ] Run the whole suite + coverage:
  `python -m coverage run --source=. --omit="tests/*" -m pytest && python -m coverage report`
  Expected: all tests pass; coverage 100%.
- [ ] Launch the app and exercise the loop end-to-end:
  `python -m streamlit run app.py` → 🔍 Detect → run `detect-windows.ps1` on this
  machine → paste its output → Load into editor → confirm the Add / Edit form is
  pre-filled → fill PSU wattage → Save → confirm it appears on Inventory.
- [ ] Then use **superpowers:finishing-a-development-branch** to open the PR.
```

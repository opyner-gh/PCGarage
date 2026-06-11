# Auto-Detect PC Specs — Design

**Date:** 2026-06-11
**Status:** Approved for planning

## Summary

PCGarage records every computer's specs by hand. This change adds a way to
**auto-detect** a machine's hardware: the app provides per-platform detection
scripts (Windows / Linux / macOS) that the user runs on a target PC. Each script
prints a JSON object — keyed to the app's record schema — describing what it
found. The user pastes that JSON into a new **🔍 Detect** page, which normalizes
it and pre-fills the **Add / Edit** form for review before saving.

The detected machine is usually **not** the machine running the app (PCGarage is
for cataloging many computers), so detection is a portable script the user runs
anywhere, not an in-app "detect this host" button.

## Goals

- Let the user populate a computer record from a script's output instead of
  typing every field.
- Support detection on Windows, Linux, and macOS via standalone scripts.
- Keep the user in control: detected data pre-fills the editor for review and
  manual completion before it is saved.
- Be robust to fields that can't be detected (notably PSU wattage) and to a
  script being slightly out of step with the schema.

## Non-Goals

- Remote/agentless detection over the network (the user runs the script
  themselves on each machine).
- An in-app "detect the host machine" button (ruled out: only ever captures one
  PC; the portable-script approach is a superset).
- Live re-syncing or polling a machine's specs over time (one-shot snapshot).
- Detecting PSU wattage/model — no sensor exposes it; always left blank.
- Validation against external hardware databases.

## Data Flow

```
Detect page → pick platform → download or copy the script
  → run the script on the TARGET PC
      → prints schema-shaped JSON to stdout
      → also writes pcgarage-detected.json next to it (a convenience copy)
  → copy the JSON → paste into the Detect page's import box → "Load into editor"
      → detection.parse_detected() normalizes it onto an empty_computer() skeleton
      → record stashed in st.session_state["detected_draft"]
      → app navigates to Add / Edit, pre-filled (Add mode)
  → user reviews, fills blanks (PSU wattage, etc.) → Save
```

The saved `pcgarage-detected.json` file is purely a convenience (a record the
user can re-open and copy from); the app itself imports via pasted text.

## Output Contract

Every script — regardless of platform — emits a **single JSON object** keyed to
the app's record schema. Each script fills what it can detect and leaves the
rest blank (`""`) or null. Warnings go to **stderr** so **stdout is clean JSON**.

```jsonc
{
  "computer_name": "<hostname>",            // suggested name; user can rename
  "os": "Windows 11 Pro 23H2",
  "cpu": {
    "manufacturer": "AMD",                  // normalized to Intel / AMD where possible
    "model": "Ryzen 5 5600X",
    "cores": 6,
    "threads": 12,
    "base_clock_ghz": 3.7,
    "boost_clock_ghz": null,                // often not exposed
    "cooler": ""                            // not detectable
  },
  "ram": {
    "manufacturer": "Corsair",              // often blank
    "capacity_gb": 32,
    "speed_mhz": 3200,
    "type": "DDR4",                         // DDR3 / DDR4 / DDR5 when known
    "configuration": "2 x 16GB"             // module count summary
  },
  "gpu": {
    "manufacturer": "NVIDIA",               // NVIDIA / AMD / Intel
    "model": "RTX 3060",
    "vram_gb": 12,                          // see VRAM caveat below
    "brand": ""                             // AIB partner — not detectable
  },
  "storage": [                              // zero or more drives
    {
      "manufacturer": "Samsung",
      "model": "980 Pro",
      "type": "NVMe SSD",                   // NVMe SSD / SATA SSD / HDD
      "capacity": "1 TB",
      "form_factor": ""                     // rarely exposed
    }
  ],
  "motherboard": {
    "model": "B550-F",
    "form_factor": ""                       // rarely exposed
  },
  "psu": {
    "model": "",                            // never detectable
    "wattage": null                         // never detectable
  }
}
```

Keys mirror `storage.empty_computer()`. A script may omit any key; import
tolerates absence.

## Detectability by Field

Setting expectations for what scripts can and can't fill:

- **Reliable:** CPU model/cores/threads/base-clock, OS name+version, RAM total
  capacity & speed & type, GPU model, drive model/capacity/SSD-vs-HDD,
  motherboard model, hostname.
- **Flaky → may be blank:**
  - **GPU VRAM** — on Windows, `Win32_VideoController.AdapterRAM` is a signed
    32-bit value that misreports cards over 4 GB; the script reads the registry
    `HardwareInformation.qwMemorySize` where available and otherwise leaves it
    blank rather than reporting a wrong number.
  - **Form factor** (motherboard and drive) — seldom exposed by the OS.
  - **RAM manufacturer** and **CPU boost clock** — inconsistent across systems.
- **Never detectable → always blank:** **PSU model & wattage**, GPU AIB brand,
  CPU cooler. These are the fields the review step exists to fill in.

## Platform Detection Notes

High-level tool mapping; exact field extraction is detailed in the plan. Each
component is detected best-effort and independently.

- **Windows (`detect-windows.ps1`, PowerShell + CIM):** `Win32_Processor`,
  `Win32_PhysicalMemory`, `Win32_VideoController` (+ registry for VRAM),
  `Win32_DiskDrive` / `MSFT_PhysicalDisk`, `Win32_BaseBoard`,
  `Win32_OperatingSystem`, `$env:COMPUTERNAME`.
- **Linux (`detect-linux.sh`, bash):** `lscpu`, `free`/`dmidecode -t memory`,
  `lspci`, `lsblk`/`/sys/block`, `dmidecode -t baseboard`, `/etc/os-release`,
  `hostname`. `dmidecode` needs root for full RAM/board detail; without it the
  script warns on stderr and leaves those fields blank.
- **macOS (`detect-macos.sh`, sh):** `system_profiler SPHardwareDataType /
  SPDisplaysDataType / SPMemoryDataType / SPStorageDataType`, `sysctl`,
  `sw_vers`, `scutil --get ComputerName`.

Scripts can't be executed in CI (they need the real OS and hardware); they are
validated manually and guarded by committed sample fixtures (see Testing).

## Module Structure

```
scripts/
  detect-windows.ps1   # PowerShell detector
  detect-linux.sh      # bash detector
  detect-macos.sh      # sh detector
detection.py           # pure logic: parse + normalize pasted JSON -> record (no Streamlit)
components/
  detect.py            # the 🔍 Detect page (script delivery + import box)
  editor.py            # (modified) consume a pending detected draft as the prefill base
app.py                 # (modified) register the Detect page in navigation
storage.py             # (modified) add DETECT_ICON + PAGE_ICONS["detect"]
tests/
  fixtures/detected-windows.json
  fixtures/detected-linux.json
  fixtures/detected-macos.json
```

- `detection.py` depends only on `storage.py` (for `empty_computer()` and the
  schema) — no Streamlit, so it is fully unit-testable.
- `components/detect.py` depends on `detection.py` and `storage.py`; it does not
  reach into the editor's internals — the hand-off is a single `session_state`
  key.

### `detection.py` — the import contract

```python
def parse_detected(text: str) -> dict:
    """Parse pasted detector JSON and normalize it onto a fresh record.

    - json.loads(text); a non-object or invalid JSON raises ValueError.
    - Start from storage.empty_computer().
    - For each scalar component, copy only known field keys; coerce numbers
      (int when the field's schema flags integer=True, else float); ignore
      unknown keys and unparseable numbers (leave the default).
    - For "storage", accept a list of dicts and keep only known per-drive keys.
    - Copy top-level "computer_name" and "os" when present (strings).
    - Never raises on missing keys — absence just leaves the skeleton default.
    """
```

The defensive normalization is what lets a script drift slightly from the schema
without breaking import: unknown keys are dropped, missing keys default, numbers
are coerced to the right type.

### Detect page (🔍)

- A platform selector (Windows / Linux / macOS).
- For the chosen platform: rendered usage instructions, the script shown in a
  copyable code block, and an `st.download_button` serving the script file from
  `scripts/`.
- An import `st.text_area` to paste the JSON, and a **"Load into editor"**
  button. On click: `parse_detected(pasted)`, store the result in
  `st.session_state["detected_draft"]`, and navigate to Add / Edit. A parse
  error is caught and shown via `st.error` with a clear message; nothing is
  stored.

### Editor integration

`components/editor.py` checks for `st.session_state["detected_draft"]` at the
start of its form render. When present (and in Add mode), it uses that record as
the prefill `base` (layered onto `empty_computer()` as edits already are) and
bumps the editor nonce so the widgets pick up the new values, then **removes**
the draft from `session_state` so later edits on rerun are not overwritten. The
existing Save path is reused unchanged — a detected record is just a pre-filled
Add. No editor logic is duplicated on the Detect page.

## Error Handling

- **Scripts:** each component is detected independently; a failure (e.g.
  `dmidecode` without root, a missing tool) emits a stderr warning and leaves
  that field blank instead of aborting. stdout always carries well-formed JSON.
- **Import:** invalid JSON or a non-object → `ValueError` → friendly `st.error`,
  no navigation, no draft stored. Partial/sparse JSON fills what is present and
  blanks the rest. Number fields that can't be coerced are left at their blank
  default rather than persisted as `0`.
- **Schema drift:** unknown keys are ignored; missing keys default — a slightly
  stale script still imports cleanly for the fields it does provide.

## Testing

`detection.py` is pure logic and gets unit tests:

- A full detected object normalizes to a complete record (values and types).
- A sparse object (missing whole components / drives) fills defaults without
  error.
- Number coercion: integer fields become `int`, float fields become `float`;
  an unparseable number leaves the default.
- Unknown keys (component-level and field-level) are dropped.
- `storage` as a list of partial drive dicts normalizes per-drive.
- Invalid JSON and a non-object top level each raise `ValueError`.

Contract fixtures: each `tests/fixtures/detected-*.json` is a representative
sample of one platform's real output; a test asserts each one feeds through
`parse_detected` to a valid record covering the expected populated keys. These
fixtures are the CI guard for the script↔schema contract since the scripts
cannot run in CI.

Detect-page AppTest: the page renders without exception; pasting a sample and
clicking "Load into editor" populates `st.session_state["detected_draft"]`; the
editor then renders pre-filled from that draft without error. Python coverage
stays at 100%.

## Scope & Phasing

One spec, one feature — but the three scripts are independent once the contract
and the import path exist. Recommended implementation order:

1. **Windows vertical slice:** `detection.py`, the Detect page, editor
   integration, `detect-windows.ps1`, its fixture, and all tests. This is a
   complete, usable feature on its own.
2. **Linux script** + fixture + contract test.
3. **macOS script** + fixture + contract test.

## Dependencies

No new Python dependencies. `st.text_area`, `st.download_button`,
`st.session_state`, and `st.navigation` are all current Streamlit.
`requirements.txt` stays `streamlit` + `pandas`. The detection scripts rely only
on tools shipped with each OS (PowerShell/CIM on Windows; coreutils + optional
`dmidecode` on Linux; `system_profiler`/`sysctl` on macOS).

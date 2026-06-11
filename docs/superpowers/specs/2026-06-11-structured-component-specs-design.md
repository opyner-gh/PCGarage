# Structured Component Specs — Design

**Date:** 2026-06-11
**Status:** Approved for planning

## Summary

PCGarage today tracks computers as flat free-text fields in a single CSV. This
change turns each major component into a structured object with optional
sub-fields (RAM speed, part manufacturers, etc.), supports a variable-length
list of storage drives per machine, migrates persistence from CSV to a nested
JSON file, splits the app into two pages (Inventory and Add / Edit), and adds an
icon to every component.

## Goals

- Capture richer, **optional** detail per component without forcing data entry.
- Support a dynamic number of storage drives per computer.
- Keep existing records intact via a one-time migration.
- Improve the UI: a dedicated read-only Inventory page and a focused Add / Edit
  page, with per-component grouping and icons.

## Non-Goals

- Filtering, sorting, or searching the inventory (future work).
- Validation of real-world correctness (e.g. confirming a CPU model exists).
- Importing specs from external hardware databases.
- Multi-user or concurrent-write support.

## Data Model

Persistence moves from `data/computers.csv` to `data/computers.json`. The file
holds a JSON array of computer objects. Every field is optional except
`computer_name`.

```jsonc
{
  "computer_name": "RYZEN-MASTER",        // required
  "created_at": "2026-04-07T16:26:28",    // ISO-8601, set on creation, preserved on edit
  "cpu": {
    "manufacturer": "AMD",                // Intel / AMD
    "model": "Ryzen 5 5600X",
    "cores": 6,
    "threads": 12,
    "base_clock_ghz": 3.7,
    "boost_clock_ghz": 4.6,
    "cooler": "Noctua NH-D15"
  },
  "ram": {
    "manufacturer": "Corsair",
    "capacity_gb": 32,
    "speed_mhz": 3600,
    "type": "DDR4",                       // DDR3 / DDR4 / DDR5
    "configuration": "2 x 16GB"
  },
  "gpu": {
    "manufacturer": "NVIDIA",             // NVIDIA / AMD / Intel
    "model": "RTX 2070 Super",
    "vram_gb": 8,
    "brand": "EVGA"                       // AIB partner
  },
  "storage": [                            // dynamic list; zero or more drives
    {
      "manufacturer": "Kingston",
      "model": "",
      "type": "NVMe SSD",                 // NVMe SSD / SATA SSD / HDD
      "capacity": "1 TB",
      "form_factor": "M.2 2280"
    }
  ],
  "motherboard": {
    "model": "ASUS ROG B550-F",           // free-text primary field
    "form_factor": "ATX"                  // ATX / Micro-ATX / Mini-ITX / E-ATX
  },
  "psu": {
    "model": "EVGA 750 G5",               // free-text primary field
    "wattage": 750
  },
  "notes": "sim rig"                       // free text
}
```

### Field schema as a single source of truth

`storage.py` defines the component/field schema declaratively so the form,
viewer, and summary table all read from one place. Each component entry carries:

- `key` (e.g. `cpu`), display `label` (e.g. "CPU"), and `icon` (emoji).
- A list of fields, each with: `key`, `label`, `widget` type
  (`text` / `number` / `select`), and (for selects) the allowed `options`.

Component icons: 🖥️ Computer · 🧠 CPU · 🧩 RAM · 🎮 GPU · 💾 Storage ·
🔩 Motherboard · 🔌 PSU · 📝 Notes. Page icons: 📦 Inventory · ✏️ Add / Edit.
Icons live in the schema and can be changed in one place.

### Required fields

Only `computer_name` is required. All component sub-fields are optional,
consistent with the "optional details" framing. The old required flags on CPU
and RAM are dropped (they no longer map to a single string).

## Migration

On startup, `migrate_csv_if_present()` runs once:

1. If `data/computers.json` already exists, do nothing.
2. Else if `data/computers.csv` exists, read it and convert each row to the new
   nested shape, then write `data/computers.json`.
3. The old CSV is left in place (renamed to `computers.csv.bak`) so nothing is
   destroyed.

Because the old values are loose strings, mapping is conservative — each legacy
value goes into the single most sensible field and the rest stay blank:

| Old column   | New location                                  |
|--------------|-----------------------------------------------|
| Computer Name| `computer_name`                               |
| CPU          | `cpu.model`                                   |
| RAM          | `ram.capacity_gb` if it parses as a number, else `ram.configuration` |
| GPU          | `gpu.model`                                   |
| Storage      | a single drive: `storage[0].model`            |
| Motherboard  | `motherboard.model`                           |
| PSU          | `psu.model`                                   |
| Notes        | `notes`                                        |
| Created At   | `created_at`                                   |

Nothing is lost; the user refines migrated records in the UI afterward.

## Pages & Module Structure

Two pages, wired with Streamlit's `st.navigation` / `st.Page` API.

```
app.py              # entry point: page config + st.navigation wiring only
storage.py          # JSON load/save, CSV migration, schema constants — no Streamlit
components/
  inventory.py      # render the Inventory page
  editor.py         # render the Add / Edit page
  widgets.py        # shared render helpers (component detail block, summary row)
```

- Pages depend only on `storage.py` and `widgets.py`; no page reaches into
  another page's internals.
- `storage.py` exposes: the schema constants, `load_computers() -> list[dict]`,
  `save_computers(list[dict])`, `add_computer(dict)`, `update_computer(index, dict)`,
  and `migrate_csv_if_present()`.

### Inventory page (📦, read-only)

- Selectbox to pick a computer (label: name + created-at).
- Full structured detail rendered as per-component blocks with icons; **only
  filled fields are shown**, so sparse machines stay clean. Drives render as a
  compact table.
- Bottom: a flattened "all computers" summary table — one row per machine with
  one-line CPU / RAM / GPU summaries and a drive count, rather than raw JSON.

### Add / Edit page (✏️)

- Mode selector: "Add new" vs "Edit existing" (edit disabled until ≥1 record).
- Computer Name at top, always visible (required).
- Each component grouped in its own `st.expander` with its icon in the label.
- Per-field widgets: `number_input` for cores/threads/clocks/capacity/speed/
  wattage; `selectbox` for constrained choices (CPU manufacturer, RAM type, GPU
  manufacturer, motherboard form-factor); `text_input` otherwise.
- **Drives:** edited with `st.data_editor(..., num_rows="dynamic")` — an editable
  table with add/delete rows and dropdowns for Type and Form Factor. This is the
  clean way to support dynamic drive slots, since add/remove buttons do not work
  inside an `st.form`. The drives editor is committed together with the form on
  Save.
- On save: Add appends a new record with a fresh `created_at`; Edit updates the
  selected record and **preserves** its original `created_at`.

## Error Handling

- Missing `computer_name` on submit → inline `st.error`, no write.
- Corrupt/unreadable JSON → surface a clear error and fall back to an empty list
  rather than crashing.
- Number fields left blank persist as absent (not `0`), so empty stays empty.
- Migration is idempotent and non-destructive (guarded by the JSON-exists check;
  old CSV backed up).

## Testing

`storage.py` is pure logic (no Streamlit) and gets unit tests:

- Round-trip: `save_computers` then `load_computers` returns equivalent data.
- Migration: a sample legacy CSV converts to the expected nested shape, including
  the RAM numeric-vs-text branch and single-drive storage mapping.
- Optional fields: records with missing/blank sub-fields load and save without
  error and without coercing blanks to `0`.
- Idempotency: migration does nothing when JSON already exists.

Page render functions stay thin and are verified by running the app.

## Dependencies

No new dependencies. `st.navigation` / `st.Page` and `st.data_editor` are part of
current Streamlit. `requirements.txt` stays `streamlit` + `pandas`.

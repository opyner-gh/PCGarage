from __future__ import annotations

import csv
import json
import re
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


def load_computers(path: Path = JSON_PATH) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_computers(computers: list[dict], path: Path = JSON_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(computers, handle, indent=2)


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


def _capacity_gb(value: str):
    """Parse a clean "<n> GB" capacity, else None.

    Anchored on purpose: a multi-token legacy value like "2 x 16GB" or
    "DDR4 3200" must be preserved verbatim as free-text configuration rather
    than mis-parsed into a stray embedded integer.
    """
    match = re.fullmatch(r"(\d+)\s*gb", value.strip(), re.IGNORECASE)
    return int(match.group(1)) if match else None


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
    capacity = _capacity_gb(ram)
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


def is_notes_present(record: dict) -> bool:
    return bool((record.get("notes") or "").strip())

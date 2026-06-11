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

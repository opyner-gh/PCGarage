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

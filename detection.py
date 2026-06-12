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
    # storage has only text/select fields, so every value is a cleaned string.
    row = storage.empty_component(storage.STORAGE_COMPONENT)
    for field in storage.STORAGE_COMPONENT["fields"]:
        if field["key"] in drive:
            row[field["key"]] = _clean_str(drive[field["key"]])
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
        record[storage.STORAGE_COMPONENT["key"]] = normalized

    return record

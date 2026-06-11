from __future__ import annotations

import copy
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
        # Layer the stored record onto a complete skeleton so missing
        # component keys never KeyError, and deepcopy so editing does not
        # mutate the loaded list in place.
        base = storage.empty_computer()
        base.update(copy.deepcopy(computers[edit_index]))
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

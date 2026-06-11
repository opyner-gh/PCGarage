from __future__ import annotations

import copy
from datetime import datetime

import pandas as pd
import streamlit as st

import storage


def _field_input(scope: str, component_key: str, field: dict, current):
    """Render one widget for a field; return its value (None/"" when empty).

    The widget key is scoped to the record being edited so that switching
    records rebuilds the widget and honours the new ``value``/``index`` instead
    of retaining the previously edited record's value from session_state.
    """
    key = f"{scope}_{component_key}_{field['key']}"
    label = field["label"]
    if field["widget"] == "number":
        value = None if current in (None, "") else current
        step = 1 if field.get("integer") else None
        return st.number_input(label, value=value, step=step, key=key)
    if field["widget"] == "select":
        options = field["options"]
        index = options.index(current) if current in options else 0
        return st.selectbox(label, options=options, index=index, key=key)
    return st.text_input(label, value=current or "", key=key)


def _storage_editor(scope: str, drives: list[dict]) -> list[dict]:
    component = storage.STORAGE_COMPONENT
    columns = [f["key"] for f in component["fields"]]
    labels = {f["key"]: f["label"] for f in component["fields"]}
    frame = pd.DataFrame(drives or [], columns=columns)

    column_config = {}
    for field in component["fields"]:
        if field["widget"] == "select":
            # Keep "" in the options so an unset drive cell (new rows, migrated
            # drives) is a valid choice rather than being flagged invalid.
            column_config[field["key"]] = st.column_config.SelectboxColumn(
                labels[field["key"]], options=field["options"])
        else:
            column_config[field["key"]] = st.column_config.TextColumn(
                labels[field["key"]])

    edited = st.data_editor(
        frame, num_rows="dynamic", width="stretch", hide_index=True,
        column_config=column_config, key=f"storage_editor_{scope}",
    )
    records = edited.fillna("").to_dict("records")
    # Drop fully-empty rows the user added but left blank.
    return [r for r in records if any(str(v).strip() for v in r.values())]


def _collect(scope: str, record: dict) -> dict:
    for component in storage.SCALAR_COMPONENTS:
        with st.expander(f"{component['icon']} {component['label']}"):
            for field in component["fields"]:
                record[component["key"]][field["key"]] = _field_input(
                    scope, component["key"], field,
                    record[component["key"]].get(field["key"]))
    with st.expander(f"{storage.STORAGE_COMPONENT['icon']} Storage", expanded=True):
        record["storage"] = _storage_editor(scope, record.get("storage", []))
    record["notes"] = st.text_area(
        f"{storage.NOTES_ICON} Notes", value=record.get("notes") or "",
        key=f"notes_{scope}")
    return record


def render() -> None:
    st.title(f"{storage.PAGE_ICONS['editor']} Add / Edit")

    try:
        computers = storage.load_computers()
    except Exception as error:
        st.error(f"Could not read saved computers: {error}")
        computers = []

    _editor_form(computers)


@st.fragment
def _editor_form(computers: list[dict]) -> None:
    """The mode picker and form, isolated in a fragment so switching mode or
    computer re-renders only this region instead of reflowing the whole page."""
    if computers:
        editing = st.radio(
            "Mode", ["Add new", "Edit existing"], horizontal=True) == "Edit existing"
        # Always render the picker (disabled in Add mode) so toggling modes
        # never adds/removes a row and shifts the form below it.
        selected = st.selectbox(
            "Computer to edit",
            options=list(range(len(computers))),
            format_func=lambda i: computers[i].get("computer_name") or "Unnamed",
            disabled=not editing,
        )
        edit_index = selected if editing else None
    else:
        edit_index = None
        st.info("Save at least one computer before you can edit.")

    if edit_index is not None:
        # Layer the stored record onto a complete skeleton so missing
        # component keys never KeyError, and deepcopy so editing does not
        # mutate the loaded list in place.
        base = storage.empty_computer()
        base.update(copy.deepcopy(computers[edit_index]))
    else:
        base = storage.empty_computer()

    # Scope every widget key to (a) the record being edited, so switching
    # records reloads its values, and (b) a per-save nonce, so a successful save
    # yields fresh widget keys — clearing the Add form and dropping the stale
    # data_editor edit-state that would otherwise duplicate just-saved drives.
    nonce = st.session_state.get("editor_nonce", 0)
    target = f"edit{edit_index}" if edit_index is not None else "add"
    scope = f"{target}_{nonce}"

    name = st.text_input("Computer Name *", value=base.get("computer_name", ""),
                          key=f"name_{scope}")

    record = _collect(scope, base)
    record["computer_name"] = name.strip()

    if st.button("Save", type="primary"):
        if not record["computer_name"]:
            st.error("Computer Name is required.")
            return
        try:
            if edit_index is not None:
                storage.update_computer(edit_index, record)
                st.success("Computer updated.")
            else:
                record["created_at"] = datetime.now().isoformat(timespec="seconds")
                storage.add_computer(record)
                st.success("Computer saved.")
        except IndexError:
            st.error("That computer no longer exists. "
                     "Reload the page and try again.")
            return
        except Exception as error:  # disk full, permissions, corrupt store, ...
            st.error(f"Could not save changes: {error}")
            return
        # Bump the nonce so the form re-renders with fresh, empty widgets.
        st.session_state["editor_nonce"] = nonce + 1
        st.rerun()

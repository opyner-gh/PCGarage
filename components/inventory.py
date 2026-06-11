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

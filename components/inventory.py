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

    _selected_detail(computers)

    st.divider()
    st.subheader("All Computers")
    table = pd.DataFrame([widgets.summary_row(c) for c in computers])
    st.dataframe(table, width="stretch", hide_index=True)


@st.fragment
def _selected_detail(computers: list[dict]) -> None:
    """Selector plus the detail cards, isolated in a fragment so picking a
    different computer re-renders only this region — the page title above and
    the summary table below stay put instead of reflowing."""
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

    st.header(f"{storage.COMPUTER_ICON} "
              f"{record.get('computer_name') or 'Unnamed Computer'}")
    os_name = record.get("os")
    if widgets.is_filled(os_name):
        st.caption(f"{storage.OS_ICON} {os_name}")
    created = record.get("created_at")
    if created:
        st.caption(f"Added {created}")
    st.divider()

    # Even card grid: the five scalar components plus a Notes card fill two
    # rows of three, so every card has the same width and consistent framing.
    grid = [("component", component) for component in storage.SCALAR_COMPONENTS]
    grid.append(("notes", None))
    for start in range(0, len(grid), 3):
        for col, (kind, component) in zip(st.columns(3), grid[start:start + 3]):
            with col.container(border=True):
                if kind == "component":
                    widgets.render_component_detail(
                        component, record.get(component["key"], {}))
                else:
                    widgets.card_title(storage.NOTES_ICON, "Notes")
                    notes = record.get("notes")
                    if widgets.is_filled(notes):
                        st.write(notes)
                    else:
                        st.caption("Not recorded")

    # Storage spans full width — its drive table needs the room.
    with st.container(border=True):
        widgets.render_storage_detail(record.get("storage", []))

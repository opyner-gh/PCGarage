from __future__ import annotations

import pandas as pd
import streamlit as st

import storage


def is_filled(value) -> bool:
    """True for any real value, including 0; False for None and empty string."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def summarize_component(key: str, data: dict) -> str:
    """One-line summary of a scalar component's filled fields, in schema order."""
    component = storage.COMPONENTS_BY_KEY[key]
    parts = [str(data.get(f["key"])) for f in component["fields"]
             if is_filled(data.get(f["key"]))]
    return " · ".join(parts)


def summary_row(record: dict) -> dict:
    row = {"Computer": record.get("computer_name", ""),
           "OS": record.get("os", "")}
    for component in storage.SUMMARY_COMPONENTS:
        key = component["key"]
        row[component["label"]] = summarize_component(key, record.get(key, {}))
    row["Drives"] = len(record.get("storage", []))
    row["Created At"] = record.get("created_at", "")
    return row


def card_title(icon: str, label: str) -> None:
    """Consistent heading used for every detail card."""
    st.markdown(f"**{icon} {label}**")


def render_component_detail(component: dict, data: dict) -> None:
    """Render a scalar component's filled fields as a compact card body."""
    card_title(component["icon"], component["label"])
    filled = [(f["label"], data.get(f["key"]))
              for f in component["fields"] if is_filled(data.get(f["key"]))]
    if not filled:
        st.caption("Not recorded")
        return
    st.markdown("\n".join(f"- **{label}:** {value}" for label, value in filled))


def render_storage_detail(drives: list[dict]) -> None:
    component = storage.STORAGE_COMPONENT
    card_title(component["icon"], component["label"])
    if not drives:
        st.caption("Not recorded")
        return
    columns = [f["key"] for f in component["fields"]]
    labels = {f["key"]: f["label"] for f in component["fields"]}
    frame = (pd.DataFrame(drives).reindex(columns=columns)
             .fillna("").rename(columns=labels))
    st.dataframe(frame, width="stretch", hide_index=True)

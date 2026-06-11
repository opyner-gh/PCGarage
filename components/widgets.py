from __future__ import annotations

import streamlit as st

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


def render_component_detail(component: dict, data: dict) -> None:
    """Render a scalar component's filled fields under an icon heading."""
    filled = [(f["label"], data.get(f["key"]))
              for f in component["fields"] if is_filled(data.get(f["key"]))]
    st.markdown(f"#### {component['icon']} {component['label']}")
    if not filled:
        st.caption("No details recorded.")
        return
    for label, value in filled:
        st.write(f"**{label}:** {value}")


def render_storage_detail(drives: list[dict]) -> None:
    component = _component_by_key("storage")
    st.markdown(f"#### {component['icon']} {component['label']}")
    if not drives:
        st.caption("No drives recorded.")
        return
    import pandas as pd
    columns = [f["key"] for f in component["fields"]]
    labels = {f["key"]: f["label"] for f in component["fields"]}
    frame = pd.DataFrame(drives).reindex(columns=columns).rename(columns=labels)
    st.dataframe(frame, width="stretch", hide_index=True)

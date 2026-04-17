from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


DATA_DIR = Path("data")
CSV_PATH = DATA_DIR / "computers.csv"
CSV_COLUMNS = [
    "Computer Name",
    "CPU",
    "RAM",
    "GPU",
    "Storage",
    "Motherboard",
    "PSU",
    "Notes",
    "Created At",
]
EDITABLE_COLUMNS = [
    "Computer Name",
    "CPU",
    "RAM",
    "GPU",
    "Storage",
    "Motherboard",
    "PSU",
    "Notes",
]


def ensure_csv_exists() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        pd.DataFrame(columns=CSV_COLUMNS).to_csv(CSV_PATH, index=False)


def load_records() -> pd.DataFrame:
    ensure_csv_exists()
    df = pd.read_csv(CSV_PATH)
    missing_columns = [col for col in CSV_COLUMNS if col not in df.columns]
    for col in missing_columns:
        df[col] = ""
    return df[CSV_COLUMNS]


def append_record(record: dict[str, str]) -> None:
    df_new = pd.DataFrame([record], columns=CSV_COLUMNS)
    df_new.to_csv(CSV_PATH, mode="a", header=False, index=False)


def save_dataframe(df: pd.DataFrame) -> None:
    ensure_csv_exists()
    df[CSV_COLUMNS].to_csv(CSV_PATH, index=False)


def update_record(row_index: int, fields: dict[str, str]) -> None:
    df = load_records()
    if row_index not in df.index:
        raise ValueError(f"Invalid row index: {row_index}")
    for col in EDITABLE_COLUMNS:
        if col in fields:
            df.loc[row_index, col] = fields[col]
    save_dataframe(df)


def cell_str(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def format_computer_option(row: pd.Series) -> str:
    name = str(row.get("Computer Name", "")).strip() or "Unnamed Computer"
    created_at = str(row.get("Created At", "")).strip()
    return f"{name} ({created_at})" if created_at else name


def main() -> None:
    st.set_page_config(page_title="Computer Specs Tracker", layout="centered")
    st.title("Computer Specs Tracker")
    st.write("View saved computer specs, add new entries, or update existing ones.")

    ensure_csv_exists()
    records = load_records()

    selected_index: int | None = None
    selected_record: pd.Series | None = None

    st.subheader("Computer Viewer")
    if records.empty:
        st.info("No computers saved yet. Add one using the form below to view details.")
    else:
        options = records.index.tolist()
        selected_index = st.selectbox(
            "Select a computer",
            options=options,
            format_func=lambda idx: format_computer_option(records.loc[idx]),
        )
        selected_record = records.loc[selected_index]

        st.markdown("### Selected Computer Specifications")
        left_col, right_col = st.columns(2)
        with left_col:
            st.write(f"**Computer Name:** {selected_record['Computer Name'] or '-'}")
            st.write(f"**CPU:** {selected_record['CPU'] or '-'}")
            st.write(f"**RAM:** {selected_record['RAM'] or '-'}")
            st.write(f"**GPU:** {selected_record['GPU'] or '-'}")
            st.write(f"**Storage:** {selected_record['Storage'] or '-'}")
        with right_col:
            st.write(f"**Motherboard:** {selected_record['Motherboard'] or '-'}")
            st.write(f"**PSU:** {selected_record['PSU'] or '-'}")
            st.write(f"**Created At:** {selected_record['Created At'] or '-'}")
            st.write(f"**Notes:** {selected_record['Notes'] or '-'}")

    st.subheader("Add or edit computer")
    if records.empty:
        mode = "Add new"
        st.info("Save at least one computer before you can use Edit existing.")
    else:
        mode = st.radio(
            "Mode",
            ["Add new", "Edit existing"],
            horizontal=True,
        )

    clear_on_submit = mode == "Add new"
    with st.form("unified_computer_form", clear_on_submit=clear_on_submit):
        if (
            mode == "Edit existing"
            and not records.empty
            and selected_index is not None
            and selected_record is not None
        ):
            computer_name = st.text_input(
                "Computer Name *",
                value=cell_str(selected_record["Computer Name"]),
                key=f"edit_{selected_index}_name",
            )
            cpu = st.text_input(
                "CPU *",
                value=cell_str(selected_record["CPU"]),
                key=f"edit_{selected_index}_cpu",
            )
            ram = st.text_input(
                "RAM *",
                value=cell_str(selected_record["RAM"]),
                key=f"edit_{selected_index}_ram",
            )
            gpu = st.text_input(
                "GPU",
                value=cell_str(selected_record["GPU"]),
                key=f"edit_{selected_index}_gpu",
            )
            storage = st.text_input(
                "Storage",
                value=cell_str(selected_record["Storage"]),
                key=f"edit_{selected_index}_storage",
            )
            motherboard = st.text_input(
                "Motherboard",
                value=cell_str(selected_record["Motherboard"]),
                key=f"edit_{selected_index}_motherboard",
            )
            psu = st.text_input(
                "PSU",
                value=cell_str(selected_record["PSU"]),
                key=f"edit_{selected_index}_psu",
            )
            notes = st.text_area(
                "Notes",
                value=cell_str(selected_record["Notes"]),
                key=f"edit_{selected_index}_notes",
            )
            submitted = st.form_submit_button("Save changes")
        else:
            computer_name = st.text_input("Computer Name *", key="unified_add_name")
            cpu = st.text_input("CPU *", key="unified_add_cpu")
            ram = st.text_input("RAM *", key="unified_add_ram")
            gpu = st.text_input("GPU", key="unified_add_gpu")
            storage = st.text_input("Storage", key="unified_add_storage")
            motherboard = st.text_input("Motherboard", key="unified_add_motherboard")
            psu = st.text_input("PSU", key="unified_add_psu")
            notes = st.text_area("Notes", key="unified_add_notes")
            submitted = st.form_submit_button("Save new computer")

    if submitted:
        required_fields = {
            "Computer Name": computer_name.strip(),
            "CPU": cpu.strip(),
            "RAM": ram.strip(),
        }
        missing = [label for label, value in required_fields.items() if not value]
        if missing:
            st.error(f"Please fill in required fields: {', '.join(missing)}.")
        elif mode == "Edit existing" and not records.empty and selected_index is not None:
            update_record(
                selected_index,
                {
                    "Computer Name": computer_name.strip(),
                    "CPU": cpu.strip(),
                    "RAM": ram.strip(),
                    "GPU": gpu.strip(),
                    "Storage": storage.strip(),
                    "Motherboard": motherboard.strip(),
                    "PSU": psu.strip(),
                    "Notes": notes.strip(),
                },
            )
            st.success("Computer updated in CSV.")
            st.rerun()
        else:
            record = {
                "Computer Name": computer_name.strip(),
                "CPU": cpu.strip(),
                "RAM": ram.strip(),
                "GPU": gpu.strip(),
                "Storage": storage.strip(),
                "Motherboard": motherboard.strip(),
                "PSU": psu.strip(),
                "Notes": notes.strip(),
                "Created At": datetime.now().isoformat(timespec="seconds"),
            }
            append_record(record)
            st.success("Computer saved to CSV.")
            st.rerun()

    st.subheader("Saved Computers")
    if records.empty:
        st.info("No computers saved yet.")
    else:
        st.dataframe(records, use_container_width=True)


if __name__ == "__main__":
    main()

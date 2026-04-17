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
    st.write("View saved computer specs and add new computers to the CSV file.")

    ensure_csv_exists()
    records = load_records()

    st.subheader("Computer Viewer")
    if records.empty:
        st.info("No computers saved yet. Add one from the form to view details.")
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

        st.markdown("#### Edit selected computer")
        with st.form("edit_computer_form"):
            edit_name = st.text_input(
                "Computer Name *",
                value=cell_str(selected_record["Computer Name"]),
                key=f"edit_{selected_index}_name",
            )
            edit_cpu = st.text_input(
                "CPU *",
                value=cell_str(selected_record["CPU"]),
                key=f"edit_{selected_index}_cpu",
            )
            edit_ram = st.text_input(
                "RAM *",
                value=cell_str(selected_record["RAM"]),
                key=f"edit_{selected_index}_ram",
            )
            edit_gpu = st.text_input(
                "GPU",
                value=cell_str(selected_record["GPU"]),
                key=f"edit_{selected_index}_gpu",
            )
            edit_storage = st.text_input(
                "Storage",
                value=cell_str(selected_record["Storage"]),
                key=f"edit_{selected_index}_storage",
            )
            edit_motherboard = st.text_input(
                "Motherboard",
                value=cell_str(selected_record["Motherboard"]),
                key=f"edit_{selected_index}_motherboard",
            )
            edit_psu = st.text_input(
                "PSU",
                value=cell_str(selected_record["PSU"]),
                key=f"edit_{selected_index}_psu",
            )
            edit_notes = st.text_area(
                "Notes",
                value=cell_str(selected_record["Notes"]),
                key=f"edit_{selected_index}_notes",
            )
            edit_submitted = st.form_submit_button("Save changes")

        if edit_submitted:
            required_edit = {
                "Computer Name": edit_name.strip(),
                "CPU": edit_cpu.strip(),
                "RAM": edit_ram.strip(),
            }
            missing_edit = [label for label, value in required_edit.items() if not value]
            if missing_edit:
                st.error(f"Please fill in required fields: {', '.join(missing_edit)}.")
            else:
                update_record(
                    selected_index,
                    {
                        "Computer Name": edit_name.strip(),
                        "CPU": edit_cpu.strip(),
                        "RAM": edit_ram.strip(),
                        "GPU": edit_gpu.strip(),
                        "Storage": edit_storage.strip(),
                        "Motherboard": edit_motherboard.strip(),
                        "PSU": edit_psu.strip(),
                        "Notes": edit_notes.strip(),
                    },
                )
                st.success("Computer updated in CSV.")
                st.rerun()

    st.subheader("Add / Save Computer")
    with st.form("computer_specs_form", clear_on_submit=True):
        computer_name = st.text_input("Computer Name *")
        cpu = st.text_input("CPU *")
        ram = st.text_input("RAM *")
        gpu = st.text_input("GPU")
        storage = st.text_input("Storage")
        motherboard = st.text_input("Motherboard")
        psu = st.text_input("PSU")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save Computer")

    if submitted:
        required_fields = {
            "Computer Name": computer_name.strip(),
            "CPU": cpu.strip(),
            "RAM": ram.strip(),
        }
        missing = [label for label, value in required_fields.items() if not value]
        if missing:
            st.error(f"Please fill in required fields: {', '.join(missing)}.")
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

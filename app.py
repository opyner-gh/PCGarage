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


def main() -> None:
    st.set_page_config(page_title="Computer Specs Tracker", layout="centered")
    st.title("Computer Specs Tracker")
    st.write("Add a computer's hardware details and save them to a CSV file.")

    ensure_csv_exists()

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

    st.subheader("Saved Computers")
    records = load_records()
    if records.empty:
        st.info("No computers saved yet.")
    else:
        st.dataframe(records, use_container_width=True)


if __name__ == "__main__":
    main()

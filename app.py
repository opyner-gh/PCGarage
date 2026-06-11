from __future__ import annotations

import streamlit as st

import storage
from components import inventory, editor


def main() -> None:
    st.set_page_config(page_title="PCGarage", layout="wide")
    try:
        storage.migrate_csv_if_present()
    except Exception as error:  # never let a migration failure brick the app
        st.error(f"Could not migrate existing data: {error}. "
                 "Your original data/computers.csv is unchanged.")

    pages = [
        st.Page(inventory.render, title="Inventory", url_path="inventory",
                icon=storage.PAGE_ICONS["inventory"], default=True),
        st.Page(editor.render, title="Add / Edit", url_path="add-edit",
                icon=storage.PAGE_ICONS["editor"]),
    ]
    st.navigation(pages).run()


if __name__ == "__main__":
    main()

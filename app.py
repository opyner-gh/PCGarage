from __future__ import annotations

import streamlit as st

import storage
from components import inventory, editor, detect


def main() -> None:
    st.set_page_config(page_title="PCGarage", layout="wide")
    try:
        storage.migrate_csv_if_present()
    except Exception as error:  # never let a migration failure brick the app
        st.error(f"Could not migrate existing data: {error}. "
                 "Your original data/computers.csv is unchanged.")

    pages = {
        "inventory": st.Page(inventory.render, title="Inventory",
                             url_path="inventory",
                             icon=storage.PAGE_ICONS["inventory"], default=True),
        "editor": st.Page(editor.render, title="Add / Edit", url_path="add-edit",
                          icon=storage.PAGE_ICONS["editor"]),
        "detect": st.Page(detect.render, title="Detect", url_path="detect",
                          icon=storage.PAGE_ICONS["detect"]),
    }
    # Expose the Page objects so a page can switch to another (Detect -> editor).
    # st.switch_page needs the StreamlitPage object for callable-defined pages.
    st.session_state["_pages"] = pages
    st.navigation(list(pages.values())).run()


if __name__ == "__main__":
    main()

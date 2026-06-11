from __future__ import annotations

from pathlib import Path

import streamlit as st

import storage
import detection

# Detection scripts are source, not user data — resolve them relative to this
# package so the page works regardless of the process's working directory.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"

# Platforms grow as their scripts land (Linux in Task 6, macOS in Task 7).
PLATFORMS = {
    "Windows": {
        "file": "detect-windows.ps1",
        "lang": "powershell",
        "run": "powershell -ExecutionPolicy Bypass -File .\\detect-windows.ps1",
    },
}


def render() -> None:
    st.title(f"{storage.PAGE_ICONS['detect']} Detect")
    st.write(
        "Run a detection script on the target PC, then paste its JSON output "
        "below to pre-fill a new computer for review.")

    platform = st.selectbox("Platform", options=list(PLATFORMS))
    spec = PLATFORMS[platform]
    script_text = (SCRIPTS_DIR / spec["file"]).read_text(encoding="utf-8")

    st.markdown(
        f"1. Download or copy **{spec['file']}** and run it on the target PC:\n\n"
        f"   ```\n   {spec['run']}\n   ```\n"
        "2. Copy the JSON it prints (a `pcgarage-detected.json` copy is also "
        "saved next to the script).\n"
        "3. Paste it below and click **Load into editor**.")
    st.download_button(f"⬇️ Download {spec['file']}", data=script_text,
                       file_name=spec["file"])
    with st.expander("Or copy the script"):
        st.code(script_text, language=spec["lang"])

    st.divider()
    pasted = st.text_area("Paste the script's JSON output here", height=220,
                          key="detect_paste")
    if st.button("Load into editor", type="primary"):
        if not pasted.strip():
            st.error("Paste the detection output first.")
            return
        try:
            record = detection.parse_detected(pasted)
        except ValueError as error:
            st.error(f"Couldn't read that detection output: {error}")
            return
        st.session_state["detected_draft"] = record
        pages = st.session_state.get("_pages")
        if pages:
            st.switch_page(pages["editor"])  # pragma: no cover (AppTest can't drive callable-page nav)
        else:
            st.success("Loaded. Open the **Add / Edit** page to review and save.")

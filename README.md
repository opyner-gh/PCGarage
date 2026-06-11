# PCGarage

A small [Streamlit](https://streamlit.io/) app for tracking your computers'
hardware specifications. Browse your builds on an **Inventory** page and create
or update them on an **Add / Edit** page. Data is stored locally as JSON — no
database or account required.

## Features

- **Inventory** page: browse saved computers with per-component detail cards and
  an "all computers" summary table.
- **Add / Edit** page: one form to add a new computer or edit an existing one.
- Structured, **optional** detail per component — manufacturer, RAM speed/type,
  CPU clocks, GPU VRAM, PSU wattage, motherboard form factor, and more.
- **Dynamic storage**: add or remove as many drives per computer as the build needs.
- Dark "ops dashboard" theme (Fira Sans / Fira Code).
- Data saved as nested JSON; a legacy `computers.csv` is migrated automatically
  on first run (and backed up to `computers.csv.bak`).

## Quick Start

**Prerequisites:** Python 3.10+ (developed on 3.12).

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd PCGarage

# 2. (Recommended) create and activate a virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

Streamlit prints a local URL (default <http://localhost:8501>) and opens it in
your browser. That's it — start adding computers on the **Add / Edit** page.

> If `streamlit` isn't found on your PATH, use `python -m streamlit run app.py`.

## Where your data lives

Records are saved to `data/computers.json` (created automatically). On first
launch, any existing `data/computers.csv` is converted to JSON and the original
is preserved as `data/computers.csv.bak`. The repo ships two sample computers so
the app isn't empty on first run.

## Running the tests

The test tooling (pytest, coverage) lives in `requirements-dev.txt`, which also
pulls in the runtime deps:

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Optional coverage report:

```bash
python -m coverage run --source=. --omit="tests/*" -m pytest && python -m coverage report
```

## Project layout

| Path | Responsibility |
|------|----------------|
| `app.py` | Entry point: page config, startup migration, navigation |
| `storage.py` | Component schema + JSON load/save/migrate (pure logic, no Streamlit) |
| `components/inventory.py` | The Inventory page |
| `components/editor.py` | The Add / Edit page |
| `components/widgets.py` | Shared render/format helpers |
| `.streamlit/config.toml` | Theme |
| `tests/` | Unit + page (AppTest) tests |
| `requirements.txt` | Runtime dependencies (Streamlit, pandas) |
| `requirements-dev.txt` | Test dependencies (pytest, coverage) + the runtime deps |

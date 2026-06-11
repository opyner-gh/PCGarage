# PCGarage

Simple Streamlit app to manually track computer hardware specifications and save them to a CSV file.

## Features

- Two pages: **Inventory** (browse saved computers) and **Add / Edit** (create or
  update entries)
- Structured, optional detail per component (manufacturer, RAM speed, clocks, etc.)
- Dynamic storage: add or remove as many drives per computer as the build needs
- Icons for every component
- Data saved as nested JSON; legacy `computers.csv` is migrated automatically on
  first run (and backed up to `computers.csv.bak`)

## Setup

1. Create and activate a virtual environment (optional but recommended)
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Storage

Records are saved to `data/computers.json`. On first launch, any existing
`data/computers.csv` is converted to JSON and the original is preserved as
`data/computers.csv.bak`.
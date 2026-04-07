# PCGarage

Simple Streamlit app to manually track computer hardware specifications and save them to a CSV file.

## Features

- Enter computer specs in a clean form UI
- Save each entry to `data/computers.csv`
- Auto-create CSV file with headers if it does not exist
- Preview all saved records directly in the app

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

## CSV Storage

Records are saved to:

`data/computers.csv`
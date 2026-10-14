# 🏊‍♀️ Swim Journey

A Streamlit dashboard that makes Riya Kalro's swimming progress visible and motivating.

## Features (Phase 1)

- Reads results from a **public Google Sheet** (`Results` tab) — no API keys, no OAuth.
- Sidebar: Google Sheet URL input, swimmer selector, filters (stroke, distance, course, date range, meet), reset, and refresh.
- Metric cards: total swims, distinct events, personal bests (all time and in date range).
- Interactive Plotly charts:
  - Swim time progression per event (dates on x-axis, faster = up).
  - Running personal-best progression (step chart).
- Personal-best table grouped by course (SCY / SCM / LCM never mixed).
- Recent swims table, newest first, with ⭐ PB markers.
- Graceful errors for bad links, permission issues, missing columns, empty sheets, and malformed rows. Failed loads are never replaced with demo data.

## Google Sheet setup

1. Create a Google Sheet using the provided template (a tab named **`Results`** with these columns):
   `Swimmer Name, Swim Date, Meet Name, Distance, Stroke, Course, Time, Result Type, Notes, Source URL`
2. Click **Share → General access → "Anyone with the link" → Viewer**.
3. Copy the sheet URL.

The app reads the sheet through Google's public visualization CSV endpoint
(`https://docs.google.com/spreadsheets/d/<ID>/gviz/tq?tqx=out:csv&sheet=Results`),
which works for link-shared sheets without any credentials. The only permission
requirement is the "Anyone with the link – Viewer" setting above.

## Setup & run

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Then paste the Google Sheet URL into the sidebar.

## Tests

```bash
pytest -v
```

## Project structure

```
app.py                      # Streamlit entry point
config.py                   # constants
components/                 # UI: filters, metric cards, charts
services/                   # Google Sheets fetching, swim analytics
utils/                      # time parsing, validation/normalization
tests/                      # pytest suite
```

## Limitations (by design, Phase 1)

- Single data source (the Google Sheet); no scraping, auth, or database.
- Response times depend on Google's public endpoint; results are cached 5 minutes.
- Only official, non-DQ, non-relay individual results count toward personal bests; rows with missing result status are not treated as official.

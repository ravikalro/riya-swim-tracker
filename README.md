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

## Features (Phase 2)

- **Motivational Standards page**: compares Riya's personal bests against the
  official **USA Swimming 2024–2028 Age Group Motivational Standards**
  (B → BB → A → AA → AAA → AAAA) for every individual event and course
  (SCY / SCM / LCM — never mixed).
- Age-group views: **10 & Under Girls (current)** and **11–12 Girls (next,
  clearly labeled as a future target)**, viewable separately or side by side.
  Age-group selection is always explicit — it never auto-switches.
- Summary cards (events with a best time, levels reached, latest milestone),
  an event-by-event comparison table with the six standard times, a next-target
  column, and an event deep-dive chart with all six standards as reference
  lines and the personal best marked.
- Encouraging, kid-friendly language; standards are presented as motivation,
  not qualification.

## Motivational standards data

- **Source document**: "USA Swimming 2024–2028 Motivational Standards" (Age Group),
  printed 10/10/2025.
- **Source URL**:
  `https://websitedevsa.blob.core.windows.net/sitefinity/docs/default-source/timesdocuments/time-standards/2025/2028-motivational-standards-age-group.pdf`
- The PDF is checked into `data/standards/usa_swimming_2024_2028_motivational_standards.pdf`.
- The extracted dataset is `data/standards/motivational_standards.json`
  (482 records, all age groups 10&U–17-18, both genders, SCY/SCM/LCM; relay
  rows excluded). The JSON carries full metadata: source URL, title, levels,
  and extraction date. The app reads only this local file — no network access
  is needed at runtime.
- **To update the standards in the future**: download the new PDF over the old
  one, then run:

  ```bash
  python pipeline/extract_standards.py
  ```

  The extractor fails loudly (non-zero exit) on any row it cannot parse or
  validate (including non-monotonic standards), so a bad parse can never
  silently ship. After extraction, run `pytest` — the suite re-validates the
  dataset and checks >15 manually verified values straight from the PDF.

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
app.py                      # Streamlit entry point (Dashboard + Motivational Standards tabs)
config.py                   # constants
components/                 # UI: filters, metric cards, charts, standards page
services/                   # Google Sheets fetching, swim analytics, standards service
utils/                      # time parsing, validation/normalization
pipeline/                   # one-off tooling: PDF -> standards JSON extractor
data/standards/             # source PDF + extracted motivational standards JSON
tests/                      # pytest suite
```

## Limitations (by design, Phase 1)

- Single data source (the Google Sheet); no scraping, auth, or database.
- Response times depend on Google's public endpoint; results are cached 5 minutes.
- Only official, non-DQ, non-relay individual results count toward personal bests; rows with missing result status are not treated as official.

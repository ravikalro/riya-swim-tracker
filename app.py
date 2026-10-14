"""Swim Journey — a swim progress dashboard for Riya Kalro."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
import streamlit as st

import config
from components import charts, filters, metric_cards, standards_page
from services import swim_analytics
from services.google_sheets_service import SheetReadError, fetch_results_frame
from utils.validation import extract_spreadsheet_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout="wide",
)

# Simple, clean styling
st.markdown(
    """
    <style>
    .big-title { font-size: 2.4rem; font-weight: 800; color: #0e5aa8; }
    .subtitle { font-size: 1.15rem; color: #666; margin-bottom: 0.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner=False)
def load_data(spreadsheet_id: str) -> tuple[pd.DataFrame, list]:
    raw, fetch_warnings = fetch_results_frame(
        spreadsheet_id, config.RESULTS_TAB_NAME, config.EXPECTED_COLUMNS
    )
    df, clean_warnings = swim_analytics.clean_results(raw)
    return df, fetch_warnings + clean_warnings


def main() -> None:
    st.markdown(
        f'<div class="big-title">{config.PAGE_ICON} {config.PAGE_TITLE}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="subtitle">{config.SUBTITLE}</div>', unsafe_allow_html=True)

    # --- Sidebar: data source ---
    st.sidebar.header("📊 Data Source")
    sheet_url = st.sidebar.text_input(
        "Google Sheet URL",
        value=st.session_state.get(
            "sheet_url",
            "https://docs.google.com/spreadsheets/d/1PwKtgkpA6aYcydN6Z7tFeuCD9oJ921Ri/edit?usp=drive_link&ouid=114445204783246626437&rtpof=true&sd=true",
        ),
        placeholder="https://docs.google.com/spreadsheets/d/…",
        help="Share the sheet with 'Anyone with the link – Viewer'.",
    )
    st.session_state["sheet_url"] = sheet_url

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()

    if not sheet_url.strip():
        st.info(
            "👋 Welcome! To see your swim results, paste the link to your "
            "Google Sheet in the sidebar on the left. "
            "Make sure the sheet is shared with **Anyone with the link – Viewer**."
        )
        return

    spreadsheet_id = extract_spreadsheet_id(sheet_url)
    if not spreadsheet_id:
        st.error(
            "That doesn't look like a Google Sheets link. "
            "It should look like `https://docs.google.com/spreadsheets/d/…`."
        )
        return

    # --- Fetch data ---
    with st.spinner("Loading your swim results… 🌊"):
        try:
            df, warnings = load_data(spreadsheet_id)
        except SheetReadError as exc:
            st.error(f"Couldn't load your swim results: {exc}")
            st.caption(
                "Tip: open the sheet in your browser, click Share → "
                "'Anyone with the link' → Viewer."
            )
            st.session_state.pop("last_refresh", None)
            return

    st.session_state["last_refresh"] = datetime.now()

    st.sidebar.success(
        f"✅ Connected — last updated {st.session_state['last_refresh'].strftime('%H:%M:%S')}"
    )
    for w in warnings:
        st.warning(w)

    if df.empty:
        st.info(
            "The sheet loaded, but there are no valid results yet. "
            "Add swims to the `Results` tab and press **Refresh Data**."
        )
        return

    # --- Swimmer + filters ---
    st.sidebar.header("🔍 Filters")
    swimmer = filters.swimmer_filter(df, config.DEFAULT_SWIMMER)
    swimmer_df = df[df["swimmer"] == swimmer]
    if swimmer_df.empty:
        st.info(f"No results found for **{swimmer}** yet. Try another swimmer.")
        return

    # --- Main navigation ---
    tab_dashboard, tab_standards = st.tabs(["🏠 Dashboard", "🎯 Motivational Standards"])

    with tab_dashboard:
        filtered = filters.result_filters(swimmer_df)

        # --- Metrics ---
        metric_cards.render_metric_cards(swimmer_df, filtered)
        st.divider()

        # --- Progression for a selected event ---
        selection = filters.event_selector(filtered)
        if selection is not None:
            stroke, distance, course = selection
            event_df = filtered[
                (filtered["stroke"] == stroke)
                & (filtered["distance"] == distance)
                & (filtered["course"] == course)
            ]
            charts.render_progression_charts(event_df, f"{distance} {stroke} ({course})")
        else:
            st.info("No events match the current filters.")
        st.divider()

        # --- PB table + recent swims ---
        charts.render_pb_table(swimmer_df)
        st.divider()
        charts.render_recent_swims(filtered)

    with tab_standards:
        standards_page.render_standards_page(swimmer_df)

    st.caption(
        "Data source: Google Sheets (public link, read-only). "
        f"Results are refreshed automatically every {config.CACHE_TTL_SECONDS // 60} minutes."
    )


if __name__ == "__main__":
    main()

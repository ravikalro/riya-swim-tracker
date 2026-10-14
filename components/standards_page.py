"""Motivational Standards page: compare personal bests against the USA
Swimming 2024-2028 Age Group Motivational Standards.

Child-friendly, encouraging UI. Standards are guidance, never pressure.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.standards_service import (
    LEVELS,
    StandardsError,
    build_comparison,
    load_metadata,
    load_standards,
    lookup_standards,
)
from utils.time_utils import format_seconds

CURRENT_AGE_GROUP = "10 & under"
NEXT_AGE_GROUP = "11-12"

LEVEL_EMOJI = {
    "B": "🌟", "BB": "🌟🌟", "A": "🥉", "AA": "🥈", "AAA": "🥇", "AAAA": "🏆"
}


def _fmt(seconds) -> str:
    if seconds is None:
        return "—"
    return format_seconds(seconds)


def _delta_text(seconds) -> str:
    if seconds is None:
        return "—"
    return f"{seconds:+.2f} s (drop {seconds:.2f}s)"


@st.cache_data(show_spinner=False)
def _load_records():
    return load_standards()


def render_standards_page(swimmer_df: pd.DataFrame) -> None:
    """Render the whole Motivational Standards page for one swimmer."""
    st.header("🎯 Motivational Standards")

    try:
        records = _load_records()
        metadata = load_metadata()
    except StandardsError as exc:
        st.error(str(exc))
        return

    st.caption(
        f"Compared against the **{metadata.get('title', 'USA Swimming Motivational Standards')}**, "
        f"extracted from the official document on {metadata.get('extraction_date', '?')}. "
        "These are motivational standards — milestones to aim for, not pressure! 💙"
    )

    girls_records = [r for r in records if r.gender == "Girls"]

    # --- Age group selector (explicit, never auto-switched) ---
    st.subheader("👧 Age Group")
    age_choice = st.radio(
        "Which age group do you want to see?",
        options=[CURRENT_AGE_GROUP, NEXT_AGE_GROUP, "Both side by side"],
        index=0,
        horizontal=True,
        format_func=lambda a: {
            CURRENT_AGE_GROUP: "🏊 Current: 10 & Under Girls",
            NEXT_AGE_GROUP: "🔭 Next: 11–12 Girls (future target)",
            "Both side by side": "⚖️ Compare both age groups",
        }[a],
    )
    if age_choice in (NEXT_AGE_GROUP, "Both side by side"):
        st.caption(
            "The 11–12 group is shown for motivation and planning. "
            "Riya is currently a 10 & Under swimmer — the next group is a future target."
        )

    # --- E. Filters ---
    with st.expander("🔍 Filters", expanded=False):
        key_prefix = "std"
        if st.button("Reset filters", key=f"{key_prefix}_reset"):
            for k in list(st.session_state):
                if isinstance(k, str) and k.startswith(f"{key_prefix}_"):
                    del st.session_state[k]
            st.rerun()
        c1, c2, c3 = st.columns(3)
        courses_avail = sorted(swimmer_df["course"].unique())
        strokes_avail = sorted(swimmer_df["stroke"].unique())
        distances_avail = sorted(int(d) for d in swimmer_df["distance"].unique())
        sel_courses = c1.multiselect("Course", courses_avail, default=courses_avail, key=f"{key_prefix}_courses")
        sel_strokes = c2.multiselect("Stroke", strokes_avail, default=strokes_avail, key=f"{key_prefix}_strokes")
        sel_distances = c3.multiselect("Distance", distances_avail, default=distances_avail, key=f"{key_prefix}_distances")

    filtered = swimmer_df[
        swimmer_df["course"].isin(sel_courses)
        & swimmer_df["stroke"].isin(sel_strokes)
        & swimmer_df["distance"].isin(sel_distances)
    ]
    # Only official, individual (non-relay) results count — already enforced by is_official.
    eligible = filtered[filtered["is_official"]]

    if age_choice == "Both side by side":
        _render_side_by_side(eligible, girls_records)
    else:
        _render_single_group(eligible, girls_records, age_choice)


def _render_single_group(eligible: pd.DataFrame, girls_records, age_group: str) -> None:
    is_next = age_group == NEXT_AGE_GROUP
    label = "🔭 Next Age Group — 11–12 Girls (future target)" if is_next else "🏊 Current Age Group — 10 & Under Girls"
    st.subheader(label)
    rows, flags = build_comparison(eligible, girls_records, age_group)
    for w in flags:
        st.warning(f"⚠️ {w}")
    _render_summary(rows, eligible, age_group)
    _render_table(rows, age_group)
    _render_detail(eligible, girls_records, age_group)


def _render_summary(rows, eligible: pd.DataFrame, age_group: str) -> None:
    st.subheader("📋 Your Milestones at a Glance")
    n_events = len(rows)
    level_counts = {lv: sum(1 for r in rows if r["achieved"] == lv) for lv in LEVELS}
    no_level = sum(1 for r in rows if r["achieved"] is None)

    cols = st.columns(4)
    cols[0].metric("Age group", age_group)
    cols[1].metric("Events with a best time", n_events)
    achieved_total = n_events - no_level
    cols[2].metric("At a standard level", achieved_total)
    if achieved_total:
        highest = max(
            (r["achieved"] for r in rows if r["achieved"]),
            key=lambda lv: LEVELS.index(lv),
        )
        cols[3].metric("Highest level reached", f"{LEVEL_EMOJI[highest]} {highest}")
    else:
        cols[3].metric("Highest level reached", "Keep swimming! 💪")

    if n_events:
        badges = " · ".join(
            f"{LEVEL_EMOJI[lv]} {lv}: {level_counts[lv]}"
            for lv in reversed(LEVELS) if level_counts[lv]
        )
        if badges:
            st.write(badges)
        if no_level:
            st.caption(
                f"{no_level} event(s) don't have a B time yet — every swim is practice for the next milestone!"
            )

    # Most recent milestone, only if reliably dated
    dated = [r for r in rows if r["achieved"] and pd.notna(r["pb_date"])]
    if dated:
        latest = max(dated, key=lambda r: r["pb_date"])
        st.success(
            f"🎉 Latest milestone: **{LEVEL_EMOJI[latest['achieved']]} {latest['achieved']}** in "
            f"**{latest['event']} ({latest['course']})** at "
            f"{latest['pb_date'].strftime('%b %d, %Y')} — {_fmt(latest['pb_seconds'])}!"
        )


def _render_table(rows, age_group: str) -> None:
    st.subheader("📊 Event-by-Event — How Your Best Times Compare")
    if not rows:
        st.info(
            "No results match the current filters — swim more events or reset the filters to see your progress here!"
        )
        return

    display = []
    for r in rows:
        achieved = (
            f"{LEVEL_EMOJI[r['achieved']]} {r['achieved']}"
            if r["achieved"] else "Not yet at B"
        )
        if r["at_highest"]:
            achieved = "🏆 AAAA — highest level in this chart!"
            next_txt = "You've reached the top! 🌈"
            delta_txt = "—"
        elif r["next_target"]:
            next_txt = f"Your next target is {r['next_target']}"
            delta_txt = _delta_text(r["seconds_to_next"])
        else:
            next_txt = "—"
            delta_txt = "—"
        display.append(
            {
                "Event": r["event"],
                "Course": r["course"],
                "⭐ Your Best": r["pb_display"],
                "Date": r["pb_date"].strftime("%b %d, %Y") if pd.notna(r["pb_date"]) else "",
                "Level": achieved,
                **{lv: _fmt(r["standards"][lv]) for lv in LEVELS},
                "🎯 Your next milestone": next_txt,
                "Time to drop": delta_txt,
            }
        )
    df = pd.DataFrame(display)

    def _highlight(row):
        styles = [""] * len(row)
        level = row["Level"]
        for lv in LEVELS:
            col = df.columns.get_loc(lv)
            if (row["Level"].startswith(LEVEL_EMOJI[lv]) and f" {lv}" in row["Level"]) or (
                level.startswith("🏆") and lv == "AAAA"
            ):
                styles[col] = "background-color: #ffe9a8; font-weight: bold"
        try:
            nxt = row["🎯 Your next milestone"].split()[-1]
            if nxt in LEVELS:
                styles[df.columns.get_loc(nxt)] = (
                    styles[df.columns.get_loc(nxt)]
                    + "; background-color: #d4ecff"
                ).lstrip("; ")
        except Exception:
            pass
        return styles

    st.dataframe(
        df.style.apply(_highlight, axis=1),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "🟡 Yellow = the standard you've achieved. 🔵 Blue = your next milestone. "
        "Lower time = faster = higher level!"
    )


def _render_side_by_side(eligible: pd.DataFrame, girls_records) -> None:

    st.subheader("⚖️ Now vs. Next — Same Best Times, Two Age Groups")
    st.caption(
        "This compares the **same personal-best times** against two different "
        "standards: the 10 & Under group (now) and the 11–12 group (future). "
        "The 11–12 standards are faster, so a level may change — that's normal "
        "and it's exactly what makes the next group a fun new mountain to climb! 🏔️"
    )
    cur_rows, cur_flags = build_comparison(eligible, girls_records, CURRENT_AGE_GROUP)
    nxt_rows, nxt_flags = build_comparison(eligible, girls_records, NEXT_AGE_GROUP)
    for w in set(cur_flags + nxt_flags):
        st.warning(f"⚠️ {w}")

    nxt_by_key = {(r["stroke"], r["distance"], r["course"]): r for r in nxt_rows}
    display = []
    for r in cur_rows:
        key = (r["stroke"], r["distance"], r["course"])
        nxt = nxt_by_key.get(key)
        cur_ach = r["achieved"] or "—"
        if r["at_highest"]:
            cur_next = "Top reached! 🏆"
        elif r["next_target"]:
            cur_next = f"{r['next_target']} (−{r['seconds_to_next']:.2f}s)"
        else:
            cur_next = "B (−{:.2f}s)".format(r["seconds_to_next"]) if r["seconds_to_next"] is not None else "—"
        if nxt is None:
            nxt_ach, nxt_next = "No standard", "—"
        else:
            nxt_ach = "🏆 AAAA (top!)" if nxt["at_highest"] else (nxt["achieved"] or "Not yet at B")
            if nxt["at_highest"]:
                nxt_next = "Top reached! 🏆"
            elif nxt["next_target"]:
                nxt_next = f"{nxt['next_target']} (−{nxt['seconds_to_next']:.2f}s)"
            else:
                nxt_next = "—"
        display.append(
            {
                "Event": r["event"],
                "Course": r["course"],
                "⭐ Your Best": r["pb_display"],
                "10 & Under level": cur_ach,
                "10&U next target": cur_next,
                "11–12 level (future)": nxt_ach,
                "11–12 next target (future)": nxt_next,
            }
        )
    if display:
        st.dataframe(pd.DataFrame(display), use_container_width=True, hide_index=True)
        st.info(
            "Same swim, two scoreboards. You're already swimming great — the 11–12 "
            "goals just give you something new and exciting to chase next year! 🚀"
        )
    else:
        st.info("No results match the current filters — reset them to compare age groups!")


def _render_detail(eligible: pd.DataFrame, girls_records, age_group: str) -> None:
    if eligible.empty:
        return
    st.subheader("🔎 Event Deep-Dive")
    options = (
        eligible[["stroke", "distance", "course"]]
        .drop_duplicates()
        .sort_values(["stroke", "distance", "course"])
    )
    labels = [f"{int(r.distance)} {r.stroke} ({r.course})" for r in options.itertuples()]
    choice = st.selectbox("Pick an event", labels, key="std_detail_event")
    i = labels.index(choice)
    row = options.iloc[i]
    stroke, distance, course = row["stroke"], int(row["distance"]), row["course"]

    rec, warn = lookup_standards(girls_records, age_group, "Girls", stroke, distance, course)
    if rec is None:
        st.warning(f"⚠️ {warn}")
        return

    event_df = eligible[
        (eligible["stroke"] == stroke)
        & (eligible["distance"] == distance)
        & (eligible["course"] == course)
    ].sort_values("date")
    pb_seconds = float(event_df["time_seconds"].min())

    fig = go.Figure()
    colors = {
        "B": "#90caf9", "BB": "#64b5f6", "A": "#42a5f5",
        "AA": "#ffb74d", "AAA": "#ff8a65", "AAAA": "#d4af37",
    }
    x0, x1 = event_df["date"].min(), event_df["date"].max()
    if x0 == x1:
        x0, x1 = x0 - pd.Timedelta(days=7), x1 + pd.Timedelta(days=7)
    for lv in LEVELS:  # faster (higher level) must sit higher on the chart
        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[rec.standards[lv]] * 2,
                mode="lines",
                name=f"{lv}: {format_seconds(rec.standards[lv])}",
                line=dict(color=colors[lv], width=2, dash="dash"),
            )
        )
    fig.add_trace(
        go.Scatter(
            x=event_df["date"],
            y=event_df["time_seconds"],
            mode="lines+markers",
            name="Your swims",
            marker=dict(size=10, color="#1f77b4"),
            customdata=list(
                zip(
                    event_df["date"].dt.strftime("%b %d, %Y"),
                    event_df["time_display"],
                    event_df["meet"],
                )
            ),
            hovertemplate="%{customdata[0]}<br>Time: %{customdata[1]}<br>Meet: %{customdata[2]}<extra>Swim</extra>",
        )
    )
    fig.add_hline(
        y=pb_seconds,
        line=dict(color="#2ca02c", width=3),
        annotation_text=f"⭐ Your Best: {format_seconds(pb_seconds)}",
        annotation_position="top left",
    )
    fig.update_yaxes(autorange="reversed", title_text="Time (seconds) — faster is up! ⬆️")
    fig.update_xaxes(title_text="Date")
    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=20, b=10),
        title=f"{distance} {stroke} ({course}) — your journey vs. {age_group} Girls standards",
        legend=dict(orientation="h"),
        yaxis_exponentformat="none",
    )
    st.plotly_chart(fig, use_container_width=True)

    from services.standards_service import determine_level

    lvl = determine_level(pb_seconds, rec.standards)
    if lvl.at_highest:
        st.balloons()
        st.success("🏆 AAAA achieved — that's the highest level in this chart! Amazing, Riya!")
    elif lvl.achieved:
        st.success(
            f"{LEVEL_EMOJI[lvl.achieved]} You've reached the **{lvl.achieved}** level in this event! "
            f"Your next target is **{lvl.next_target}** at "
            f"{format_seconds(rec.standards[lvl.next_target])} — just "
            f"**{lvl.seconds_to_next:.2f} seconds** to drop. You're getting closer! 💪"
        )
    else:
        st.info(
            f"🌟 Your next milestone: the **B** standard at {format_seconds(rec.standards['B'])}. "
            f"Drop **{lvl.seconds_to_next:.2f} seconds** and you'll get there. We believe in you!"
        )

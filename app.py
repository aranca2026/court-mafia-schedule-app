
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from data_loader import (
    build_leaderboard,
    category_summary,
    filter_schedule,
    get_categories,
    get_courts,
    get_players,
    load_tournament_data,
    player_fixtures,
    upcoming_matches,
)

st.set_page_config(
    page_title="Tournament Schedule App",
    page_icon="🏸",
    layout="wide",
)

st.title("🏸 Tournament Schedule App")
st.caption("Upload your Excel workbook or use the bundled workbook to publish a mobile-friendly schedule dashboard.")

with st.sidebar:
    st.header("Data source")
    uploaded_file = st.file_uploader("Upload tournament workbook", type=["xlsx"])
    st.markdown(
        "The app expects the workbook to contain at least the **Schedule** sheet. "
        "If the **Registrations** sheet exists, player search becomes more reliable."
    )

try:
    data = load_tournament_data(uploaded_file)
except Exception as exc:
    st.error(f"Could not load workbook: {exc}")
    st.stop()

schedule = data["schedule"]
registrations = data["registrations"]

if schedule.empty:
    st.warning("No usable rows were found in the Schedule sheet.")
    st.stop()

categories = ["All"] + get_categories(schedule)
courts = ["All"] + get_courts(schedule)

st.markdown("---")
c1, c2, c3, c4 = st.columns(4)
with c1:
    selected_category = st.selectbox("Category", categories)
with c2:
    selected_court = st.selectbox("Court", courts)
with c3:
    selected_status = st.selectbox("Status", ["All", "Scheduled", "TBD"])
with c4:
    search_text = st.text_input("Search player/team")

filtered = filter_schedule(
    schedule,
    category=None if selected_category == "All" else selected_category,
    court=None if selected_court == "All" else selected_court,
    status=None if selected_status == "All" else selected_status,
    search_text=search_text,
)

summary = category_summary(schedule)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total matches", f"{len(schedule):,}")
m2.metric("Ready to play", f"{(schedule['status'] == 'Scheduled').sum():,}")
m3.metric("TBD fixtures", f"{(schedule['status'] == 'TBD').sum():,}")
m4.metric("Categories", f"{schedule['category'].nunique():,}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview", "Full Schedule", "Court View", "Player Search", "Leaderboard"]
)

with tab1:
    left, right = st.columns([1.1, 1.3])

    with left:
        st.subheader("Category summary")
        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "category": "Category",
                "matches": st.column_config.NumberColumn("Matches", format="%d"),
                "scheduled": st.column_config.NumberColumn("Scheduled", format="%d"),
                "tbd": st.column_config.NumberColumn("TBD", format="%d"),
            },
        )

    with right:
        st.subheader("Upcoming / ready fixtures")
        nxt = upcoming_matches(filtered)
        if nxt.empty:
            st.info("No fixtures match the current filter.")
        else:
            st.dataframe(
                nxt[
                    [
                        "start_display",
                        "end_display",
                        "category",
                        "venue",
                        "court_label",
                        "round_name",
                        "match_details",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "start_display": "Start",
                    "end_display": "End",
                    "category": "Category",
                    "venue": "Venue",
                    "court_label": "Court",
                    "round_name": "Round",
                    "match_details": "Fixture",
                },
            )

with tab2:
    st.subheader("Full schedule")
    export_cols = [
        "match_id",
        "date",
        "start_display",
        "end_display",
        "category",
        "venue",
        "court_label",
        "round_name",
        "pool_no",
        "match_details",
        "status",
    ]
    st.dataframe(
        filtered[export_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "match_id": "Match ID",
            "date": "Date",
            "start_display": "Start",
            "end_display": "End",
            "category": "Category",
            "venue": "Venue",
            "court_label": "Court",
            "round_name": "Round",
            "pool_no": "Pool / Slot",
            "match_details": "Fixture",
            "status": "Status",
        },
    )
    csv = filtered[export_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered schedule (CSV)",
        data=csv,
        file_name="filtered_schedule.csv",
        mime="text/csv",
    )

with tab3:
    st.subheader("Court-wise view")
    court_values = get_courts(filtered)
    if not court_values:
        st.info("No court data available for current filter.")
    else:
        cols = st.columns(min(3, len(court_values)))
        for idx, court in enumerate(court_values):
            frame = filtered[filtered["court_label"] == court].copy()
            with cols[idx % len(cols)]:
                st.markdown(f"### {court}")
                st.dataframe(
                    frame[
                        [
                            "start_display",
                            "category",
                            "round_name",
                            "match_details",
                            "status",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "start_display": "Time",
                        "category": "Category",
                        "round_name": "Round",
                        "match_details": "Fixture",
                        "status": "Status",
                    },
                )

with tab4:
    st.subheader("Player search")
    all_players = get_players(schedule, registrations)
    chosen_player = st.selectbox(
        "Select player",
        options=[""] + all_players,
        index=0,
    )
    name_query = st.text_input("Or type a player / team name")
    q = chosen_player or name_query.strip()

    if q:
        fixtures = player_fixtures(schedule, q)
        if fixtures.empty:
            st.warning("No fixtures found for that player/team.")
        else:
            st.dataframe(
                fixtures[
                    [
                        "date",
                        "start_display",
                        "end_display",
                        "category",
                        "venue",
                        "court_label",
                        "round_name",
                        "match_details",
                        "status",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "date": "Date",
                    "start_display": "Start",
                    "end_display": "End",
                    "category": "Category",
                    "venue": "Venue",
                    "court_label": "Court",
                    "round_name": "Round",
                    "match_details": "Fixture",
                    "status": "Status",
                },
            )
    else:
        st.info("Choose or type a player name to see all their fixtures.")

with tab5:
    st.subheader("Leaderboard")
    leaderboard = build_leaderboard(schedule)
    if leaderboard.empty:
        st.info("No valid score rows were found. Update scores in Excel and re-upload the workbook.")
    else:
        leaderboard_category = st.selectbox(
            "Leaderboard category",
            ["All"] + sorted(leaderboard["category"].dropna().unique().tolist()),
        )
        lb = leaderboard if leaderboard_category == "All" else leaderboard[leaderboard["category"] == leaderboard_category]
        st.dataframe(
            lb,
            use_container_width=True,
            hide_index=True,
            column_config={
                "category": "Category",
                "team": "Team",
                "played": st.column_config.NumberColumn("Played", format="%d"),
                "won": st.column_config.NumberColumn("Won", format="%d"),
                "lost": st.column_config.NumberColumn("Lost", format="%d"),
                "points": st.column_config.NumberColumn("Points", format="%d"),
                "scored": st.column_config.NumberColumn("Scored", format="%d"),
                "conceded": st.column_config.NumberColumn("Conceded", format="%d"),
                "score_diff": st.column_config.NumberColumn("Score Diff", format="%d"),
                "win_pct": st.column_config.NumberColumn("Win %", format="%.1f%%"),
            },
        )

st.markdown("---")
st.caption(
    "Tip: publish this app on Streamlit Community Cloud, then share the link or venue QR code with players."
)

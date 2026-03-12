
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

BUNDLED_WORKBOOK = Path(__file__).with_name("tournament_schedule.xlsx")


def _read_sheet(file: Any, sheet_name: str, **kwargs) -> pd.DataFrame:
    return pd.read_excel(file, sheet_name=sheet_name, **kwargs)


def _normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if text.lower() in {"nan", "none", "0", "0.0"}:
        return ""
    return text


def _clean_schedule(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    expected = {
        "Category": "category",
        "Venue": "venue",
        "Start Time": "start_time",
        "End Time": "end_time",
        "Round Name": "round_name",
        "Court No": "court_no",
        "Pool No": "pool_no",
        "Match Details": "match_details",
        "Player 1": "player_1",
        "Player 2": "player_2",
        "Team 1 Name": "team_1_name",
        "Team 1 Score": "team_1_score",
        "Player 3": "player_3",
        "Player 4": "player_4",
        "Team 2 Name": "team_2_name",
        "Team 2 Score": "team_2_score",
        "TeamA_Code": "team_a_code",
        "TeamB_Code": "team_b_code",
    }
    keep = [c for c in expected if c in df.columns]
    df = df[keep].rename(columns=expected)

    for col in ["category", "venue", "round_name", "pool_no", "match_details",
                "player_1", "player_2", "player_3", "player_4",
                "team_1_name", "team_2_name", "team_a_code", "team_b_code"]:
        if col in df.columns:
            df[col] = df[col].map(_normalize_text)

    for dt_col in ["start_time", "end_time"]:
        if dt_col in df.columns:
            df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")

    for score_col in ["team_1_score", "team_2_score"]:
        if score_col in df.columns:
            df[score_col] = pd.to_numeric(df[score_col], errors="coerce")

    df = df[~df["category"].eq("")].copy()
    df["match_id"] = range(1, len(df) + 1)
    df["date"] = df["start_time"].dt.strftime("%d %b %Y").fillna("")
    df["start_display"] = df["start_time"].dt.strftime("%I:%M %p").str.lstrip("0").fillna("")
    df["end_display"] = df["end_time"].dt.strftime("%I:%M %p").str.lstrip("0").fillna("")
    df["court_label"] = df["court_no"].apply(lambda x: f"Court {int(x)}" if pd.notna(x) else "")

    def combine_team(row, prefix):
        players = [row.get(f"{prefix}_1", ""), row.get(f"{prefix}_2", "")]
        players = [p for p in players if p]
        return " / ".join(players)

    # Team display fallback order
    team1 = []
    team2 = []
    for _, row in df.iterrows():
        t1 = row.get("team_1_name", "") or combine_team({
            "team_1": row.get("player_1", ""),
            "team_2": row.get("player_2", ""),
        }, "team")
        t2 = row.get("team_2_name", "") or combine_team({
            "team_1": row.get("player_3", ""),
            "team_2": row.get("player_4", ""),
        }, "team")
        team1.append(t1)
        team2.append(t2)

    df["team_1_display"] = [x if x else _normalize_text(y) for x, y in zip(team1, df.get("team_1_name", ""))]
    df["team_2_display"] = [x if x else _normalize_text(y) for x, y in zip(team2, df.get("team_2_name", ""))]

    df["match_details"] = df["match_details"].where(~df["match_details"].eq(""), df["team_1_display"] + " vs " + df["team_2_display"])
    df["match_details"] = df["match_details"].str.replace(r"\s+vs\s+$", "", regex=True).str.strip()

    df["has_team_1"] = df["team_1_display"].ne("")
    df["has_team_2"] = df["team_2_display"].ne("")
    df["status"] = np.where(df["has_team_1"] & df["has_team_2"], "Scheduled", "TBD")

    return df.sort_values(["start_time", "venue", "court_no", "match_id"]).reset_index(drop=True)


def _clean_registrations(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename_map = {
        "Category": "category",
        "Code": "code",
        "Player 1": "player_1",
        "Player 2": "player_2",
        "Team ID": "team_id",
        "UPI ID": "upi_id",
        "Player 1 DUPR": "player_1_dupr",
        "Player 2 DUPR": "player_2_dupr",
    }
    if "Category" not in df.columns:
        return pd.DataFrame(columns=rename_map.values())
    df = df.rename(columns=rename_map)
    df = df[list(rename_map.values())]
    for col in df.columns:
        df[col] = df[col].map(_normalize_text)
    df = df[~df["category"].eq("")]
    return df.reset_index(drop=True)


def load_tournament_data(uploaded_file: Any | None) -> dict[str, pd.DataFrame]:
    file_source = uploaded_file if uploaded_file is not None else BUNDLED_WORKBOOK

    schedule = _read_sheet(file_source, "Schedule")
    if uploaded_file is not None:
        uploaded_file.seek(0)
    try:
        registrations = _read_sheet(file_source, "Registrations", header=2)
    except Exception:
        registrations = pd.DataFrame()

    return {
        "schedule": _clean_schedule(schedule),
        "registrations": _clean_registrations(registrations),
    }


def get_categories(schedule: pd.DataFrame) -> list[str]:
    return sorted(schedule["category"].dropna().unique().tolist())


def get_courts(schedule: pd.DataFrame) -> list[str]:
    return sorted([c for c in schedule["court_label"].dropna().unique().tolist() if c])


def filter_schedule(
    schedule: pd.DataFrame,
    category: str | None = None,
    court: str | None = None,
    status: str | None = None,
    search_text: str | None = None,
) -> pd.DataFrame:
    df = schedule.copy()
    if category:
        df = df[df["category"] == category]
    if court:
        df = df[df["court_label"] == court]
    if status:
        df = df[df["status"] == status]
    if search_text:
        q = re.escape(search_text.strip())
        mask = (
            df["match_details"].str.contains(q, case=False, na=False)
            | df["team_1_display"].str.contains(q, case=False, na=False)
            | df["team_2_display"].str.contains(q, case=False, na=False)
            | df.get("player_1", pd.Series("", index=df.index)).str.contains(q, case=False, na=False)
            | df.get("player_2", pd.Series("", index=df.index)).str.contains(q, case=False, na=False)
            | df.get("player_3", pd.Series("", index=df.index)).str.contains(q, case=False, na=False)
            | df.get("player_4", pd.Series("", index=df.index)).str.contains(q, case=False, na=False)
        )
        df = df[mask]
    return df.reset_index(drop=True)


def upcoming_matches(schedule: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    return schedule.head(limit).reset_index(drop=True)


def category_summary(schedule: pd.DataFrame) -> pd.DataFrame:
    grp = (
        schedule.groupby("category", dropna=False)
        .agg(matches=("match_id", "count"), scheduled=("status", lambda s: (s == "Scheduled").sum()), tbd=("status", lambda s: (s == "TBD").sum()))
        .reset_index()
        .sort_values(["matches", "category"], ascending=[False, True])
    )
    return grp


def get_players(schedule: pd.DataFrame, registrations: pd.DataFrame | None = None) -> list[str]:
    players = set()
    for col in ["player_1", "player_2", "player_3", "player_4"]:
        if col in schedule.columns:
            players.update([v for v in schedule[col].dropna().astype(str).tolist() if _normalize_text(v)])
    if registrations is not None and not registrations.empty:
        for col in ["player_1", "player_2"]:
            if col in registrations.columns:
                players.update([v for v in registrations[col].dropna().astype(str).tolist() if _normalize_text(v)])
    return sorted(players)


def player_fixtures(schedule: pd.DataFrame, player_name: str) -> pd.DataFrame:
    q = re.escape(player_name.strip())
    mask = (
        schedule["match_details"].str.contains(q, case=False, na=False)
        | schedule["team_1_display"].str.contains(q, case=False, na=False)
        | schedule["team_2_display"].str.contains(q, case=False, na=False)
        | schedule.get("player_1", pd.Series("", index=schedule.index)).str.contains(q, case=False, na=False)
        | schedule.get("player_2", pd.Series("", index=schedule.index)).str.contains(q, case=False, na=False)
        | schedule.get("player_3", pd.Series("", index=schedule.index)).str.contains(q, case=False, na=False)
        | schedule.get("player_4", pd.Series("", index=schedule.index)).str.contains(q, case=False, na=False)
    )
    return schedule[mask].sort_values(["start_time", "court_no"]).reset_index(drop=True)


def build_leaderboard(schedule: pd.DataFrame) -> pd.DataFrame:
    cols_needed = {"category", "team_1_display", "team_2_display", "team_1_score", "team_2_score"}
    if not cols_needed.issubset(schedule.columns):
        return pd.DataFrame()

    rows = []
    valid = schedule[
        schedule["team_1_display"].ne("")
        & schedule["team_2_display"].ne("")
        & schedule["team_1_score"].notna()
        & schedule["team_2_score"].notna()
    ].copy()

    if valid.empty:
        return pd.DataFrame()

    for _, row in valid.iterrows():
        t1 = row["team_1_display"]
        t2 = row["team_2_display"]
        s1 = float(row["team_1_score"])
        s2 = float(row["team_2_score"])
        category = row["category"]

        rows.append(
            {
                "category": category,
                "team": t1,
                "played": 1,
                "won": int(s1 > s2),
                "lost": int(s1 < s2),
                "points": 3 if s1 > s2 else 0,
                "scored": s1,
                "conceded": s2,
            }
        )
        rows.append(
            {
                "category": category,
                "team": t2,
                "played": 1,
                "won": int(s2 > s1),
                "lost": int(s2 < s1),
                "points": 3 if s2 > s1 else 0,
                "scored": s2,
                "conceded": s1,
            }
        )

    out = (
        pd.DataFrame(rows)
        .groupby(["category", "team"], as_index=False)
        .sum()
    )
    out["score_diff"] = out["scored"] - out["conceded"]
    out["win_pct"] = np.where(out["played"] > 0, (out["won"] / out["played"]) * 100, 0)
    out = out.sort_values(
        ["category", "points", "score_diff", "scored", "team"],
        ascending=[True, False, False, False, True],
    ).reset_index(drop=True)
    return out

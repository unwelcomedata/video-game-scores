#!/usr/bin/env python3
"""Pre-publish validation — re-check the video-game-scores chart data before publishing.

Run this BEFORE curating the release branch / flipping the repo public. It
re-derives what each of the four published charts should show, straight from the
DuckDB source tables, and confirms:

  1. The published export CSV (export/video_game_scores_v1.csv) matches the DuckDB
     source table (games_clean) on the key columns — no drift between DB and ship.
  2. The headline chart facts are still true (distribution mean/median/90+/70s/sub-50,
     the year-line span + crossover, the scatter correlation + outlier set), so a
     silent data change can't slip out unnoticed.
  3. Structural invariants hold (row counts; critic=0 dropped from the scatter;
     exactly 12 flagged outliers; the top-isolated game).
  4. Social vs web chart parity — the two rendered sets cover the same filenames
     and are the correct canvases.

The four published charts:
  1. Video game critic review scores  — histogram of IGDB critic ratings (hero)
  2. Video game user review scores    — histogram of IGDB user ratings (same colors)
  3. Average critic vs user by year   — two-line (critic + user)
  4. IGDB user vs critic rating        — scatter, 12 most-isolated games labelled

Exit code 0 = all checks passed, safe to publish. Non-zero = do NOT publish.

Usage:
    .venv/bin/python scripts/validate_charts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

PROJECT = Path(__file__).resolve().parent
while not (PROJECT / "config.yaml").exists() and PROJECT != PROJECT.parent:
    PROJECT = PROJECT.parent
sys.path.insert(0, str(PROJECT))
from src.ingest import load_config  # noqa: E402

failures: list[str] = []
checks: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        checks.append(f"  PASS  {name}")
    else:
        failures.append(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def approx(a: float, b: float, tol: float = 0.005) -> bool:
    if b == 0:
        return a == 0
    return abs(a - b) / abs(b) <= tol


def main() -> int:
    cfg = load_config("config.yaml")
    db = str(PROJECT / cfg["settings"]["duckdb_file"])
    export_dir = PROJECT / cfg["paths"]["export"]
    con = duckdb.connect(db, read_only=True)

    # ── Universe / row counts ─────────────────────────────────────────────
    n_games = con.execute("SELECT COUNT(*) FROM chart_critic_all").fetchone()[0]
    check("universe: 6,005 games with a critic aggregate (>= 3 outlets)",
          n_games == 6005, f"got {n_games:,}")
    check("universe: games_clean and chart_critic_all agree on row count",
          con.execute("SELECT COUNT(*) FROM games_clean").fetchone()[0] == n_games,
          "games_clean != chart_critic_all")

    # ── Charts 1 & 2 (histograms) — distribution headline facts ───────────
    mean_c, median_c, n90, n70s, nsub50 = con.execute(
        "SELECT ROUND(AVG(critic_rating),1), ROUND(MEDIAN(critic_rating),1), "
        "SUM(CASE WHEN critic_rating >= 90 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN critic_rating BETWEEN 70 AND 79.999 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN critic_rating < 50 THEN 1 ELSE 0 END) FROM chart_critic_all"
    ).fetchone()
    check("chart1: critic mean == 73.5", mean_c == 73.5, f"got {mean_c}")
    check("chart1: critic median == 75.3", median_c == 75.3, f"got {median_c}")
    check("chart1: 90+ elite count == 246", n90 == 246, f"got {n90}")
    check("chart1: 70s (the fat middle) == 2,128", n70s == 2128, f"got {n70s}")
    check("chart1: sub-50 count == 261", nsub50 == 261, f"got {nsub50}")

    # User histogram draws only games with a user rating; it must be a subset.
    n_user = con.execute(
        "SELECT COUNT(*) FROM chart_critic_all WHERE user_rating IS NOT NULL").fetchone()[0]
    check("chart2: user-rating games (5,312) is a proper subset of all games",
          0 < n_user < n_games and n_user == 5312, f"got {n_user}")
    mean_u, median_u = con.execute(
        "SELECT ROUND(AVG(user_rating),1), ROUND(MEDIAN(user_rating),1) "
        "FROM chart_critic_all WHERE user_rating IS NOT NULL").fetchone()
    check("chart2: user mean == 72.4", mean_u == 72.4, f"got {mean_u}")
    check("chart2: user median == 73.4", median_u == 73.4, f"got {median_u}")

    # ── Chart 3 (avg by year, two lines) ──────────────────────────────────
    yr = con.execute("SELECT * FROM chart_avg_by_year ORDER BY year").df()
    check("chart3: 21 year rows", len(yr) == 21, f"got {len(yr)}")
    check("chart3: spans 2001–2021", int(yr.year.min()) == 2001 and int(yr.year.max()) == 2021,
          f"got {int(yr.year.min())}–{int(yr.year.max())}")
    check("chart3: every year has >= 10 scored games",
          bool((yr.n_games >= 10).all()), "a year has < 10 games")
    check("chart3: both lines sit inside the 60–90 axis window",
          bool(((yr.avg_critic.between(60, 90)) & (yr.avg_user.between(60, 90))).all()),
          "a year's average falls outside 60–90")
    # The chart's story: users higher than critics early (2001), critics higher by the end (2021).
    first, last = yr.iloc[0], yr.iloc[-1]
    check("chart3: in 2001 users rated higher than critics",
          first.avg_user > first.avg_critic, f"2001 critic {first.avg_critic} vs user {first.avg_user}")
    check("chart3: by 2021 critics rate higher than users",
          last.avg_critic > last.avg_user, f"2021 critic {last.avg_critic} vs user {last.avg_user}")

    # ── Chart 4 (scatter, isolation outliers) ─────────────────────────────
    n_sc = con.execute("SELECT COUNT(*) FROM chart_scatter").fetchone()[0]
    check("chart4: scatter has 5,311 games (critic > 0, both ratings)",
          n_sc == 5311, f"got {n_sc}")
    check("chart4: no critic=0 rows survive (Infernal artifact dropped)",
          con.execute("SELECT COUNT(*) FROM chart_scatter WHERE critic_rating <= 0").fetchone()[0] == 0,
          "a critic<=0 row is present")
    n_out = con.execute("SELECT COUNT(*) FROM chart_scatter WHERE is_outlier").fetchone()[0]
    check("chart4: exactly 12 flagged outliers", n_out == 12, f"got {n_out}")
    r = con.execute("SELECT corr(critic_rating, user_rating) FROM chart_scatter").fetchone()[0]
    check("chart4: Pearson r ~= 0.60", approx(r, 0.605, tol=0.02), f"got {r:.3f}")
    top_iso = con.execute(
        "SELECT name FROM chart_scatter ORDER BY isolation DESC LIMIT 1").fetchone()[0]
    check("chart4: most-isolated game is 'Overlord: Fellowship of Evil'",
          top_iso == "Overlord: Fellowship of Evil", f"got {top_iso!r}")
    # Every flagged outlier must actually be among the 12 most isolated.
    flagged = set(con.execute("SELECT name FROM chart_scatter WHERE is_outlier").df()["name"])
    top12 = set(con.execute(
        "SELECT name FROM chart_scatter ORDER BY isolation DESC LIMIT 12").df()["name"])
    check("chart4: flagged outliers == the 12 most isolated points",
          flagged == top12, f"mismatch: {flagged ^ top12}")

    # ── Published CSV matches the DuckDB source (no drift) ────────────────
    cols = ["id", "name", "critic_rating", "critic_count",
            "user_rating", "user_count", "release_year"]
    src = con.execute(
        "SELECT id, name, critic_rating, critic_count, user_rating, user_count, "
        "release_year FROM games_clean").df()
    path = export_dir / "video_game_scores_v1.csv"
    if not path.exists():
        check("export: video_game_scores_v1.csv exists", False, "missing export file")
    else:
        df_csv = pd.read_csv(path)
        try:
            a = src[cols].sort_values("id").reset_index(drop=True)
            b = df_csv[cols].sort_values("id").reset_index(drop=True)
            same = a.shape == b.shape
            detail = "" if same else f"row count {a.shape[0]} vs {b.shape[0]}"
            if same:
                for col in cols:
                    if pd.api.types.is_numeric_dtype(a[col]):
                        diff = (a[col].astype("float64") - b[col].astype("float64")).abs()
                        tol = 0.05 if a[col].abs().max() <= 100 else 1.0
                        col_ok = bool(((diff <= tol) | (a[col].isna() & b[col].isna())).all())
                    else:
                        col_ok = bool((a[col].fillna("\x00").astype(str) ==
                                       b[col].fillna("\x00").astype(str)).all())
                    if not col_ok:
                        same = False
                        detail = f"column {col!r} differs"
                        break
            check("export: video_game_scores_v1.csv matches DuckDB on key columns", same,
                  (detail + " — regenerate 03-prepare") if detail else "")
        except KeyError as e:
            check(f"export: CSV has expected columns {cols}", False, str(e))

    con.close()

    # ── Social vs web chart parity ────────────────────────────────────────
    social_dir = PROJECT / "outputs" / "social"
    web_dir = PROJECT / "outputs" / "web"
    social = sorted(social_dir.glob("*.png")) if social_dir.exists() else []
    if social and web_dir.exists():
        s_names = {p.name for p in social}
        w_names = {p.name for p in web_dir.glob("*.png")}
        check("parity: social and web sets cover the same filenames", s_names == w_names,
              f"only social: {sorted(s_names - w_names)}; only web: {sorted(w_names - s_names)}")
        check("parity: exactly 4 published charts", len(s_names) == 4, f"got {len(s_names)}")
        try:
            from PIL import Image
            s_dims = {Image.open(p).size for p in social}
            w_dims = {Image.open(p).size for p in web_dir.glob("*.png")}
            check("parity: every social chart is 1600x900", s_dims == {(1600, 900)}, f"got {sorted(s_dims)}")
            check("parity: every web chart is 1664x936", w_dims == {(1664, 936)}, f"got {sorted(w_dims)}")
        except ImportError:
            pass
    else:
        checks.append("  SKIP  chart parity (outputs/ not rendered on this checkout)")

    # ── Report ────────────────────────────────────────────────────────────
    print("Pre-publish chart-data validation — video-game-scores (IGDB review scores)")
    print("=" * 60)
    for line in checks:
        print(line)
    for line in failures:
        print(line)
    print("=" * 60)
    if failures:
        print(f"RESULT: {len(failures)} FAILURE(S) — DO NOT PUBLISH.")
        return 1
    print(f"RESULT: all {len([c for c in checks if 'PASS' in c])} checks passed — safe to publish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

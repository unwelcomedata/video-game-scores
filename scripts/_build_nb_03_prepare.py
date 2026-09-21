"""Build notebooks/03-prepare.ipynb — export dataset + chart_ tables (IGDB).

Packages games_clean into a sellable CSV/Excel/Parquet + codebook, and builds
the chart_ tables the three planned charts read:
  - histogram of critic ratings (the hero)
  - 90+ critic games per year (line, cut at last complete year)
  - critic vs user rating (scatter)

    .venv/bin/python scripts/_build_nb_03_prepare.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

PROJECT = Path(__file__).resolve().parent.parent
NB = PROJECT / "notebooks" / "03-prepare.ipynb"

cells = []

cells.append(new_markdown_cell(
    "# 03 — Prepare\n"
    "\n"
    "Two outputs, both from `games_clean`:\n"
    "\n"
    "1. **Sellable export** — `export/video_game_scores_v1` as CSV + Excel + "
    "Parquet, with a plain-English **codebook** (every column described). No PII "
    "(public game metadata), so `strip_pii` is a no-op.\n"
    "2. **`chart_*` DuckDB tables** for the confirmed charts:\n"
    "   - `chart_critic_all` — one row per game (critic + user rating) → the two "
    "distribution histograms (critic and user).\n"
    "   - `chart_90plus_by_year` — count of 90+ critic games per release year, "
    "**cut at the last complete year** (recent years still accruing critic scores). "
    "(Exploration reference; not in the published social set.)\n"
    "   - `chart_avg_by_year` — mean critic vs mean user rating per year → the "
    "two-line chart.\n"
    "   - `chart_scatter` — games with BOTH ratings, `critic_rating` > 0, with an "
    "`is_outlier` flag (12 most visually-isolated points) → the user-vs-critic scatter."
))

cells.append(new_code_cell(
    "import sys, os\n"
    "from pathlib import Path\n"
    "\n"
    "PROJECT = Path.cwd()\n"
    "while not (PROJECT / 'config.yaml').exists() and PROJECT != PROJECT.parent:\n"
    "    PROJECT = PROJECT.parent\n"
    "os.chdir(PROJECT)\n"
    "sys.path.insert(0, str(PROJECT))\n"
    "\n"
    "from src.ingest import load_config\n"
    "from src.clean_quality import get_connection\n"
    "from src.prepare import package_dataset\n"
    "\n"
    "cfg = load_config('config.yaml')\n"
    "con = get_connection(cfg)\n"
    "print('games_clean rows:', con.execute('SELECT COUNT(*) FROM games_clean').fetchone()[0])"
))

cells.append(new_markdown_cell(
    "## 1. Sellable export + codebook"
))

cells.append(new_code_cell(
    "export_df = con.execute('''\n"
    "    SELECT id, name, slug, critic_rating, critic_count,\n"
    "           user_rating, user_count, release_year, decade,\n"
    "           genres, platforms\n"
    "    FROM games_clean\n"
    "    ORDER BY critic_rating DESC, name\n"
    "''').df()\n"
    "\n"
    "codebook = {\n"
    "    'id': 'IGDB internal game id (unique per game).',\n"
    "    'name': 'Game title as listed on IGDB.',\n"
    "    'slug': 'IGDB URL slug for the game.',\n"
    "    'critic_rating': 'IGDB aggregated CRITIC rating, 0-100 (unweighted mean of external critic outlet scores IGDB has collected). The distribution this project charts.',\n"
    "    'critic_count': 'Number of external critic scores behind critic_rating (>= 3 by construction).',\n"
    "    'user_rating': 'IGDB community/USER rating, 0-100 (a separate measure from the critic rating; not blended with it).',\n"
    "    'user_count': 'Number of IGDB users behind user_rating (may be null if no user ratings).',\n"
    "    'release_year': 'Year of first release, derived from the IGDB first_release_date timestamp.',\n"
    "    'decade': 'Release decade (release_year floored to the nearest 10) — for era comparisons.',\n"
    "    'genres': 'Comma-separated IGDB genres for the game.',\n"
    "    'platforms': 'Comma-separated platforms the game released on (per IGDB).',\n"
    "}\n"
    "\n"
    "notes = '''Source: IGDB — Internet Game Database (API), https://api.igdb.com/v4/games\n"
    "License: Free for non-commercial use under the Twitch Developer Services Agreement; attribution to IGDB. Fun-tier pop-culture dataset.\n"
    "Scope: games with a critic aggregate backed by >= 3 critic outlets (aggregated_rating_count >= 3).\n"
    "Metric: critic_rating is IGDB\\'s aggregate of external CRITIC scores (NOT Metacritic; a different aggregator/method). user_rating is IGDB\\'s community rating. Two separate measures, never blended.\n"
    "Caveat: IGDB aggregate is an unweighted mean of whatever outlets it has, so it varies by title/era; scores drift up over time; very recent titles may still be accruing critic scores.'''\n"
    "\n"
    "written = package_dataset(export_df, cfg, name='video_game_scores_v1', codebook=codebook, notes=notes)\n"
    "written"
))

cells.append(new_markdown_cell(
    "## 2a. `chart_critic_all` — the histogram + scatter source\n"
    "One row per game with both ratings. The histogram bins `critic_rating`; the "
    "scatter uses games that also have a `user_rating`."
))

cells.append(new_code_cell(
    "con.execute('DROP TABLE IF EXISTS chart_critic_all')\n"
    "con.execute('''CREATE TABLE chart_critic_all AS\n"
    "  SELECT id, name, critic_rating, critic_count, user_rating, user_count, release_year, decade\n"
    "  FROM games_clean''')\n"
    "print('chart_critic_all:', con.execute('SELECT COUNT(*) FROM chart_critic_all').fetchone()[0])\n"
    "print('with BOTH critic+user (scatter):', con.execute('SELECT COUNT(*) FROM chart_critic_all WHERE user_rating IS NOT NULL').fetchone()[0])"
))

cells.append(new_markdown_cell(
    "## 2b. `chart_90plus_by_year` — 90+ critic games per year\n"
    "\n"
    "Count of games with `critic_rating >= 90` by release year. We **cut at the last "
    "year whose catalogue looks complete** — determined data-drivenly below, since "
    "very recent releases are still accruing critic scores (a partial year would look "
    "like a false collapse). The cutoff year + reason go in the chart caption."
))

cells.append(new_code_cell(
    "import datetime\n"
    "this_year = datetime.date.today().year\n"
    "\n"
    "# Total scored games per year — find where recent years fall off a cliff.\n"
    "per_year = con.execute('''\n"
    "  SELECT release_year,\n"
    "         COUNT(*) AS total_scored,\n"
    "         SUM(CASE WHEN critic_rating >= 90 THEN 1 ELSE 0 END) AS n_90plus\n"
    "  FROM chart_critic_all WHERE release_year IS NOT NULL\n"
    "  GROUP BY release_year ORDER BY release_year\n"
    "''').df()\n"
    "\n"
    "# Cutoff: the last year whose total_scored is at least 40% of the recent peak\n"
    "# (a simple, defensible completeness rule). Never include the current year.\n"
    "recent = per_year[per_year.release_year >= this_year - 12]\n"
    "peak = recent['total_scored'].max()\n"
    "complete = per_year[(per_year.total_scored >= 0.4 * peak) & (per_year.release_year < this_year)]\n"
    "CUTOFF_YEAR = int(complete['release_year'].max())\n"
    "print('recent peak scored/yr:', int(peak), '| chosen cutoff year:', CUTOFF_YEAR)\n"
    "per_year.tail(12)"
))

cells.append(new_code_cell(
    "# Start the line where annual counts stabilize (>= 10 scored games/yr), through the cutoff.\n"
    "start_row = per_year[per_year.total_scored >= 10]\n"
    "START_YEAR = int(start_row['release_year'].min())\n"
    "print('line spans', START_YEAR, '→', CUTOFF_YEAR)\n"
    "\n"
    "con.execute('DROP TABLE IF EXISTS chart_90plus_by_year')\n"
    "con.execute(f'''CREATE TABLE chart_90plus_by_year AS\n"
    "  SELECT release_year AS year,\n"
    "         SUM(CASE WHEN critic_rating >= 90 THEN 1 ELSE 0 END) AS n_90plus\n"
    "  FROM chart_critic_all\n"
    "  WHERE release_year BETWEEN {START_YEAR} AND {CUTOFF_YEAR}\n"
    "  GROUP BY release_year ORDER BY release_year''')\n"
    "con.execute('SELECT * FROM chart_90plus_by_year').df()"
))

cells.append(new_markdown_cell(
    "## 2c. `chart_avg_by_year` — average critic vs user rating per year\n"
    "\n"
    "Mean critic rating and mean user rating for each release year, for the two-line "
    "chart (one line critic, one line user). Restricted to years with **≥ 10 scored "
    "games** (so early sparse years don't wobble) and cut at the **same last-complete "
    "year** as `chart_90plus_by_year` (recent partial years would distort the tail). "
    "This is the exact series the `06-viz-social` line chart reads."
))

cells.append(new_code_cell(
    "con.execute('DROP TABLE IF EXISTS chart_avg_by_year')\n"
    "con.execute(f'''CREATE TABLE chart_avg_by_year AS\n"
    "  SELECT release_year AS year,\n"
    "         ROUND(AVG(critic_rating), 1) AS avg_critic,\n"
    "         ROUND(AVG(user_rating), 1)   AS avg_user,\n"
    "         COUNT(*)                     AS n_games\n"
    "  FROM chart_critic_all\n"
    "  WHERE release_year IS NOT NULL\n"
    "  GROUP BY release_year\n"
    "  HAVING COUNT(*) >= 10 AND release_year <= {CUTOFF_YEAR}\n"
    "  ORDER BY release_year''')\n"
    "con.execute('SELECT * FROM chart_avg_by_year').df()"
))

cells.append(new_markdown_cell(
    "## 2d. `chart_scatter` — user vs critic, with visual-isolation outlier flag\n"
    "\n"
    "One row per game that has **both** a critic and user rating, for the scatter. Two "
    "prep decisions baked in here (so they live in the pipeline, not just the "
    "exploration notebook):\n"
    "\n"
    "1. **Drop the `critic_rating = 0` artifact** — a single game (Infernal) carries an "
    "aggregate of exactly 0 over 6 outlets, which is an IGDB data gap, not a real mean. "
    "It would otherwise be the most-isolated dot on the plot.\n"
    "2. **Flag the 12 most VISUALLY ISOLATED points** as outliers (`is_outlier`) — the "
    "games with the most empty space around them, measured as the mean distance to each "
    "point's **8 nearest neighbours** in normalized (0–1 per axis) score space. This is "
    "what the eye reads as \u2018standing out\u2019; it flags the lonely dots in every corner and "
    "does not over-pick the dense clusters. These are the games the scatter labels."
))

cells.append(new_code_cell(
    "import numpy as np\n"
    "N_OUTLIERS = 12\n"
    "K = 8\n"
    "\n"
    "sc = con.execute('''\n"
    "  SELECT name, critic_rating, user_rating\n"
    "  FROM chart_critic_all\n"
    "  WHERE user_rating IS NOT NULL AND critic_rating > 0\n"
    "''').df()\n"
    "\n"
    "cx = sc['critic_rating'].values.astype(float)\n"
    "uy = sc['user_rating'].values.astype(float)\n"
    "nx = (cx - cx.min()) / (cx.max() - cx.min())\n"
    "ny = (uy - uy.min()) / (uy.max() - uy.min())\n"
    "P = np.column_stack([nx, ny])\n"
    "iso = np.empty(len(P))\n"
    "for i in range(0, len(P), 500):                # chunked brute-force kNN (no scipy)\n"
    "    blk = P[i:i+500]\n"
    "    d2 = ((blk[:, None, :] - P[None, :, :]) ** 2).sum(2)\n"
    "    d2.sort(axis=1)\n"
    "    iso[i:i+500] = np.sqrt(d2[:, 1:K+1]).mean(1)\n"
    "sc['isolation'] = iso\n"
    "sc['is_outlier'] = sc.index.isin(sc['isolation'].nlargest(N_OUTLIERS).index)\n"
    "\n"
    "con.execute('DROP TABLE IF EXISTS chart_scatter')\n"
    "con.register('sc_df', sc)\n"
    "con.execute('CREATE TABLE chart_scatter AS SELECT name, critic_rating, user_rating, isolation, is_outlier FROM sc_df')\n"
    "con.unregister('sc_df')\n"
    "print('chart_scatter:', con.execute('SELECT COUNT(*) FROM chart_scatter').fetchone()[0], 'games;',\n"
    "      con.execute('SELECT COUNT(*) FROM chart_scatter WHERE is_outlier').fetchone()[0], 'flagged outliers')\n"
    "con.execute('SELECT name, critic_rating, user_rating, ROUND(isolation,3) AS isolation FROM chart_scatter WHERE is_outlier ORDER BY isolation DESC').df()"
))

cells.append(new_markdown_cell(
    "### Sanity: headline distribution facts\n"
    "The numbers a caption/validation would cite."
))

cells.append(new_code_cell(
    "con.execute('''\n"
    "SELECT COUNT(*) AS n_games,\n"
    "  ROUND(AVG(critic_rating),1) AS mean_critic,\n"
    "  ROUND(MEDIAN(critic_rating),1) AS median_critic,\n"
    "  SUM(CASE WHEN critic_rating >= 90 THEN 1 ELSE 0 END) AS n_90plus,\n"
    "  SUM(CASE WHEN critic_rating BETWEEN 70 AND 79.999 THEN 1 ELSE 0 END) AS n_70s,\n"
    "  SUM(CASE WHEN critic_rating < 50 THEN 1 ELSE 0 END) AS n_sub50\n"
    "FROM chart_critic_all\n"
    "''').df()"
))

cells.append(new_markdown_cell(
    "---\n"
    "**Next:** `04-viz.ipynb` — explore the distribution, the 90+ trend, and the "
    "critic-vs-user scatter. **Pause for owner review before `06-viz-social`.**"
))

cells.append(new_markdown_cell(
    "---\n"
    "## Cleanup\n"
    "Close the DuckDB connection so the single-writer lock is released."
))

cells.append(new_code_cell(
    "con.close()\n"
    "print('connection closed')"
))

nb = new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
})
NB.write_text(nbf.writes(nb), encoding="utf-8")
print(f"wrote {NB}")

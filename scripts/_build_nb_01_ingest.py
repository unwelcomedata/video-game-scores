"""Build notebooks/01-ingest.ipynb — IGDB games ingest.

Regenerates the ingest notebook from code so its cells stay in sync with
src/ingest.py. Run with the project venv:

    .venv/bin/python scripts/_build_nb_01_ingest.py

Narrates the IGDB pull (canonical-record rule): a markdown cell names the source
+ Twitch OAuth, and visible code cells mint the token and call the generic
src.ingest.fetch_igdb_games() driven by config.yaml.
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

PROJECT = Path(__file__).resolve().parent.parent
NB = PROJECT / "notebooks" / "01-ingest.ipynb"

cells = []

cells.append(new_markdown_cell(
    "# 01 — Ingest\n"
    "\n"
    "**Source: IGDB — Internet Game Database (API).** IGDB (owned by Twitch/Amazon) "
    "is a large, actively-maintained game database queried through its v4 API — "
    "**not scraped**. Each game can carry a `aggregated_rating` (external **critic** "
    "aggregate, 0–100), a `rating` (IGDB **user/community** rating, 0–100), release "
    "date, genres and platforms.\n"
    "\n"
    "**Why IGDB (not Metacritic/RAWG).** Metacritic aggregates a score only slowly "
    "and selectively, so recent years look artificially sparse. IGDB's critic "
    "coverage keeps up with current releases, so the story stays up to date. The "
    "metric is therefore *IGDB critic rating*, not *Metacritic*.\n"
    "\n"
    "**Auth.** IGDB uses a short-lived OAuth token minted from a free **Twitch** app "
    "(client-credentials flow). `TWITCH_CLIENT_ID` + `TWITCH_CLIENT_SECRET` live in "
    "the **gitignored `.env`** and are exchanged for a token here — never hardcoded, "
    "committed, or printed. Register an app at <https://dev.twitch.tv/console/apps>.\n"
    "\n"
    "**What we keep.** Games with a critic aggregate backed by **≥ 3 critic scores** "
    "(`aggregated_rating_count >= 3`) so a lone review doesn't create a noisy "
    "\"aggregate.\" Raw JSON pages are cached to `data/raw/igdb/`; the flattened "
    "table lands in DuckDB as `igdb_games_raw` and is registered in `_sources`."
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
    "from dotenv import load_dotenv\n"
    "from src.ingest import load_config, igdb_access_token, fetch_igdb_games, _igdb_id_name_map\n"
    "from src.clean_quality import get_connection, load_to_duckdb, register_source\n"
    "\n"
    "load_dotenv('.env')\n"
    "CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')\n"
    "CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')\n"
    "assert CLIENT_ID and CLIENT_SECRET, 'TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET missing from .env — register a free app at https://dev.twitch.tv/console/apps'\n"
    "\n"
    "cfg = load_config('config.yaml')\n"
    "con = get_connection(cfg)\n"
    "\n"
    "# Mint a short-lived IGDB OAuth token from the Twitch app credentials.\n"
    "token = igdb_access_token(CLIENT_ID, CLIENT_SECRET, cfg)\n"
    "print('Project:', cfg['project_name'])\n"
    "print('IGDB token acquired:', bool(token))"
))

cells.append(new_markdown_cell(
    "## Pull the critic-rated catalogue from IGDB\n"
    "\n"
    "`fetch_igdb_games()` (in `src/ingest.py`) POSTs Apicalypse queries to `/v4/games`, "
    "offset-paged 500 at a time, filtered to `aggregated_rating != null & "
    "aggregated_rating_count >= 3`, sorted by critic rating. Genre/platform IDs come "
    "back as arrays; we keep them here and resolve to names in the next cell. Every "
    "raw page is saved to `data/raw/igdb/`."
))

cells.append(new_code_cell(
    "df_raw = fetch_igdb_games(CLIENT_ID, token, cfg)\n"
    "print(df_raw.shape)\n"
    "df_raw.head()"
))

cells.append(new_markdown_cell(
    "## Resolve genre & platform IDs to names\n"
    "IGDB stores genres/platforms as ID arrays. Resolve them in bulk (two small "
    "reference calls) and join comma-separated name strings onto the games table."
))

cells.append(new_code_cell(
    "all_genre_ids = sorted({i for ids in df_raw['genre_ids'] for i in ids})\n"
    "all_platform_ids = sorted({i for ids in df_raw['platform_ids'] for i in ids})\n"
    "\n"
    "genre_map = _igdb_id_name_map('genres', all_genre_ids, CLIENT_ID, token, cfg)\n"
    "platform_map = _igdb_id_name_map('platforms', all_platform_ids, CLIENT_ID, token, cfg)\n"
    "print('genres:', len(genre_map), '| platforms:', len(platform_map))\n"
    "\n"
    "df_raw['genres'] = df_raw['genre_ids'].apply(lambda ids: ', '.join(genre_map.get(i, '') for i in ids))\n"
    "df_raw['platforms'] = df_raw['platform_ids'].apply(lambda ids: ', '.join(platform_map.get(i, '') for i in ids))\n"
    "df_raw = df_raw.drop(columns=['genre_ids', 'platform_ids'])\n"
    "df_raw.head()"
))

cells.append(new_markdown_cell(
    "## Load raw to DuckDB + register provenance"
))

cells.append(new_code_cell(
    "from datetime import date\n"
    "\n"
    "load_to_duckdb(df_raw, 'igdb_games_raw', con)\n"
    "\n"
    "register_source(\n"
    "    con, 'igdb_games_raw',\n"
    "    name='IGDB — Internet Game Database (API)',\n"
    "    url='https://api.igdb.com/v4/games',\n"
    "    license='Free for non-commercial use — Twitch Developer Services Agreement; attribution to IGDB',\n"
    "    notes=('Games with a critic aggregate backed by >= 3 critic scores '\n"
    "           '(aggregated_rating_count >= 3). Fields: id, slug, name, release_year, '\n"
    "           'aggregated_rating (critic 0-100), aggregated_rating_count, rating (user 0-100), '\n"
    "           'rating_count, total_rating, total_rating_count, genres, platforms. '\n"
    "           'Raw JSON pages cached in data/raw/igdb/.'),\n"
    "    retrieved=date.today().isoformat(),\n"
    "    methodology=('aggregated_rating = IGDB simple mean of external critic outlet scores (0-100); '\n"
    "                 'rating = IGDB community/user rating (0-100). Two separate measures, not blended '\n"
    "                 '(total_rating is IGDB\\'s blend, kept for reference only). Distinct from Metacritic '\n"
    "                 '(a different aggregator/method) — describe as IGDB critic rating, not Metacritic.'),\n"
    "    series_breaks=('IGDB aggregate is an unweighted mean of whatever outlets it has, so composition '\n"
    "                   'varies by title/era; low aggregated_rating_count aggregates are less stable (>=3 '\n"
    "                   'floor applied). Scores drift up over time and covered outlets change — cross-era '\n"
    "                   'comparisons are directional; bin by period. Very recent titles may still be '\n"
    "                   'accruing critic scores at pull time.'),\n"
    ")\n"
    "\n"
    "con.execute('''SELECT COUNT(*) AS n,\n"
    "  ROUND(MIN(aggregated_rating),1) AS min_c, ROUND(MAX(aggregated_rating),1) AS max_c,\n"
    "  ROUND(AVG(aggregated_rating),1) AS avg_c,\n"
    "  SUM(CASE WHEN rating IS NOT NULL THEN 1 ELSE 0 END) AS have_user_rating\n"
    "  FROM igdb_games_raw''').df()"
))

cells.append(new_markdown_cell(
    "## Quick inspection"
))

cells.append(new_code_cell(
    "print('rows:', len(df_raw))\n"
    "print('with critic aggregate:', df_raw['aggregated_rating'].notna().sum())\n"
    "print('with user rating:', df_raw['rating'].notna().sum())\n"
    "yrs = df_raw['release_year'].dropna()\n"
    "print('release years:', int(yrs.min()), '→', int(yrs.max()))\n"
    "df_raw['aggregated_rating'].describe()"
))

cells.append(new_markdown_cell(
    "---\n"
    "**Next:** `02-clean.ipynb` — clean in DuckDB, cast, derive year/decade, "
    "quality report, save interim Parquet."
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

"""Build notebooks/02-clean.ipynb — clean the IGDB games table in DuckDB.

All cleaning happens inside DuckDB (workflow rule). Casts critic/user ratings,
derives decade from release_year, trims text, drops rows missing the critic
aggregate, dedupes on game id, runs a quality report, saves interim Parquet.

    .venv/bin/python scripts/_build_nb_02_clean.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

PROJECT = Path(__file__).resolve().parent.parent
NB = PROJECT / "notebooks" / "02-clean.ipynb"

cells = []

cells.append(new_markdown_cell(
    "# 02 — Clean\n"
    "\n"
    "Clean `igdb_games_raw` **inside DuckDB** (workflow rule — no pandas transform "
    "chains) into `games_clean`:\n"
    "\n"
    "- round `aggregated_rating` (critic) and `rating` (user) to 1 dp, keep as DOUBLE;\n"
    "- cast the counts to INTEGER;\n"
    "- derive `decade` from `release_year`;\n"
    "- trim text columns; drop rows with no critic aggregate (defensive — the pull "
    "  already filtered on `aggregated_rating != null & count >= 3`);\n"
    "- dedupe on game `id` (keep the one with the most critic scores behind it);\n"
    "- `quality_report()` before saving; interim saved as **Parquet**.\n"
    "\n"
    "Both ratings are on the same 0–100 scale but are **separate measures** (critic "
    "vs user) — kept side by side, never blended. The critic aggregate is the metric "
    "the histogram plots; both feed the critic-vs-user scatter."
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
    "from src.clean_quality import get_connection, run_sql, quality_report, save_interim\n"
    "\n"
    "cfg = load_config('config.yaml')\n"
    "con = get_connection(cfg)\n"
    "print('rows in raw:', con.execute('SELECT COUNT(*) FROM igdb_games_raw').fetchone()[0])"
))

cells.append(new_markdown_cell(
    "## Build `games_clean` in DuckDB\n"
    "\n"
    "One SQL pass: round the two ratings, cast counts + year, derive `decade`, TRIM "
    "text, keep only rows with a critic aggregate in 0–100, dedupe on `id` (keep the "
    "row with the most critic outlets). `decade` supports the era-binning caveat from "
    "`SOURCES.md` (aggregates drift over time)."
))

cells.append(new_code_cell(
    "con.execute('DROP TABLE IF EXISTS games_clean')\n"
    "con.execute('''\n"
    "CREATE TABLE games_clean AS\n"
    "WITH casted AS (\n"
    "    SELECT\n"
    "        CAST(id AS BIGINT)                                   AS id,\n"
    "        TRIM(slug)                                           AS slug,\n"
    "        TRIM(name)                                           AS name,\n"
    "        ROUND(TRY_CAST(aggregated_rating AS DOUBLE), 1)      AS critic_rating,\n"
    "        TRY_CAST(aggregated_rating_count AS INTEGER)         AS critic_count,\n"
    "        ROUND(TRY_CAST(rating AS DOUBLE), 1)                 AS user_rating,\n"
    "        TRY_CAST(rating_count AS INTEGER)                    AS user_count,\n"
    "        TRY_CAST(release_year AS INTEGER)                    AS release_year,\n"
    "        TRIM(genres)                                         AS genres,\n"
    "        TRIM(platforms)                                      AS platforms\n"
    "    FROM igdb_games_raw\n"
    "),\n"
    "filtered AS (\n"
    "    SELECT *,\n"
    "        CASE WHEN release_year IS NOT NULL\n"
    "             THEN (release_year // 10) * 10 END              AS decade\n"
    "    FROM casted\n"
    "    WHERE critic_rating IS NOT NULL AND critic_rating BETWEEN 0 AND 100\n"
    "),\n"
    "deduped AS (\n"
    "    SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY critic_count DESC NULLS LAST) AS rn\n"
    "    FROM filtered\n"
    ")\n"
    "SELECT * EXCLUDE (rn) FROM deduped WHERE rn = 1\n"
    "''')\n"
    "\n"
    "run_sql('''SELECT COUNT(*) AS n,\n"
    "  ROUND(MIN(critic_rating),1) mn, ROUND(MAX(critic_rating),1) mx,\n"
    "  ROUND(AVG(critic_rating),2) mean, ROUND(MEDIAN(critic_rating),1) med,\n"
    "  SUM(CASE WHEN user_rating IS NOT NULL THEN 1 ELSE 0 END) have_user\n"
    "  FROM games_clean''', con)"
))

cells.append(new_markdown_cell(
    "## Quality report\n"
    "Null counts, dupes, and basic stats before we save the interim file."
))

cells.append(new_code_cell(
    "df_clean = con.execute('SELECT * FROM games_clean').df()\n"
    "quality_report(df_clean, 'games_clean', con, required_columns=['id', 'name', 'critic_rating'])\n"
    "df_clean.head()"
))

cells.append(new_markdown_cell(
    "## Save interim (Parquet)"
))

cells.append(new_code_cell(
    "save_interim(df_clean, cfg, 'games_clean')\n"
    "print('saved interim games_clean:', df_clean.shape)"
))

cells.append(new_markdown_cell(
    "---\n"
    "**Next:** `03-prepare.ipynb` — build the export dataset (CSV/Excel/Parquet) + "
    "codebook, and the `chart_*` tables the histogram / line / scatter read."
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

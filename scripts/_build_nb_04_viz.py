"""Build notebooks/04-viz.ipynb — explore the IGDB rating charts.

Exploration stage: the three planned charts, rendered INLINE (display-only, no
export) so the owner can confirm the framing before 06-viz-social.

Charts:
  1. Hero histogram — distribution of IGDB critic ratings, full 0-100 range,
     90+ band in AQUA (median line stays gold, so they don't read as related).
  2. Line — games scoring 90+ per release year, cut at the last complete year.
  3. Scatter — IGDB user rating vs critic rating.

Rendering: Pillow shared templates (this venv is Py3.14+matplotlib, which hits a
RecursionError on matplotlib ticks — same gotcha as dungeon-crawler-carl). Using
the real publication templates for exploration = what we explore is what we ship.

    .venv/bin/python scripts/_build_nb_04_viz.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

PROJECT = Path(__file__).resolve().parent.parent
NB = PROJECT / "notebooks" / "04-viz.ipynb"

cells = []

cells.append(new_markdown_cell(
    "# 04 — Explore the charts\n"
    "\n"
    "**The question (F4):** what is *the shape of game review scores*? Using **IGDB "
    "critic ratings** (switched from Metacritic so recent years aren't starved — "
    "IGDB's critic coverage keeps up). 6,005 games with a critic aggregate backed by "
    "≥3 outlets.\n"
    "\n"
    "**Headline facts (`03-prepare`):** mean 73.5, median 75.3; the 90+ club is only "
    "~246 games (~4%); the 70s are the fat middle (~2,100); sub-50 is rare (~260, "
    "~4%). A **left-skewed pile in the 70s–80s with a thin elite tail and a "
    "surprisingly thin bad-score tail**.\n"
    "\n"
    "Three charts explored below (display-only). **⭐ Review surface — confirm the "
    "framing before I build the polished social/web renders in `06-viz-social`.**\n"
    "\n"
    "*Rendering note: this venv (Py3.14 + matplotlib) hits the known RecursionError "
    "on matplotlib ticks, so exploration uses the shared Pillow templates — the real "
    "publication charts — rendered inline.*"
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
    "SHARED = PROJECT.parent.parent / 'shared'\n"
    "sys.path.insert(0, str(SHARED))\n"
    "\n"
    "import duckdb\n"
    "from colors import c\n"
    "from chart_templates import histogram, line_chart, scatter_plot\n"
    "from IPython.display import display\n"
    "\n"
    "from src.ingest import load_config\n"
    "cfg = load_config('config.yaml')\n"
    "con = duckdb.connect(cfg['settings']['duckdb_file'], read_only=True)\n"
    "\n"
    "df_all = con.execute('SELECT critic_rating, user_rating, release_year FROM chart_critic_all').df()\n"
    "print('games:', len(df_all))\n"
    "df_all['critic_rating'].describe()"
))

cells.append(new_markdown_cell(
    "## Chart 1 (HERO) — distribution of IGDB critic ratings\n"
    "\n"
    "Full 0–100 range, 5-point bands, mean + median lines, and the **90+ club "
    "highlighted in aqua** (deliberately NOT gold — the gold dashed line is the "
    "median, and we don't want the highlight to read as related to it). This is the "
    "F4 hero: \"the shape of game review scores.\""
))

cells.append(new_code_cell(
    "img = histogram(\n"
    "    df_all, value_col='critic_rating',\n"
    "    bin_edges=list(range(0, 101, 5)), x_range=(0, 100), x_tick_step=10,\n"
    "    x_axis_label='IGDB critic rating', y_axis_label='Number of games',\n"
    "    bar_color=c('teal'), highlight_range=(90, 100, c('aqua')),\n"
    "    title='Video game review scores \u2014 distribution of IGDB critic ratings',\n"
    "    subtitle='6,005 games (\u2265 3 critic scores each); each bar = a 5-point band. 90+ highlighted.',\n"
    "    source='IGDB',\n"
    ")\n"
    "display(img)"
))

cells.append(new_markdown_cell(
    "## Chart 2 — games scoring 90+ per year\n"
    "\n"
    "The elite tail over time. Cut at the last complete year (recent releases are "
    "still accruing critic scores, so a partial year would look like a false "
    "collapse) — the cutoff + reason are stated in the subtitle."
))

cells.append(new_code_cell(
    "by_year = con.execute('SELECT year, n_90plus FROM chart_90plus_by_year ORDER BY year').df()\n"
    "cut = int(by_year['year'].max())\n"
    "print('spans', int(by_year['year'].min()), '→', cut)\n"
    "img = line_chart(\n"
    "    by_year, x_col='year',\n"
    "    series=[{'col': 'n_90plus', 'label': '90+ games', 'color': c('teal')}],\n"
    "    x_axis_label='Release year', y_axis_label='Games scoring 90+',\n"
    "    y_min=0, value_labels=True, label_last=False, markers=True,\n"
    "    title='Video game review scores \u2014 games scoring 90+ by release year',\n"
    "    subtitle=f'IGDB critic rating. Cut at {cut}: newer releases are still accruing critic scores, so later years would undercount.',\n"
    "    source='IGDB',\n"
    ")\n"
    "display(img)"
))

cells.append(new_markdown_cell(
    "## Chart 3 — user rating vs critic rating\n"
    "\n"
    "Do IGDB users agree with critics? Point per game (the ~5,300 with both a critic "
    "and a user rating). Look for the correlation and where they diverge."
))

cells.append(new_code_cell(
    "df_scatter = con.execute('SELECT critic_rating, user_rating FROM chart_critic_all WHERE user_rating IS NOT NULL').df()\n"
    "print('games with both ratings:', len(df_scatter))\n"
    "corr = df_scatter['critic_rating'].corr(df_scatter['user_rating'])\n"
    "print('Pearson r:', round(corr, 3))\n"
    "img = scatter_plot(\n"
    "    df_scatter, x_col='critic_rating', y_col='user_rating',\n"
    "    x_axis_label='IGDB critic rating', y_axis_label='IGDB user rating',\n"
    "    point_color=c('teal'),\n"
    "    title='Video game review scores \u2014 IGDB user rating vs critic rating',\n"
    "    subtitle=f'{len(df_scatter):,} games with both a critic and a user rating (0\u2013100). Pearson r = {corr:.2f}.',\n"
    "    source='IGDB',\n"
    ")\n"
    "display(img)"
))

cells.append(new_markdown_cell(
    "## Score-band table (caption numbers)"
))

cells.append(new_code_cell(
    "con.execute('''\n"
    "SELECT\n"
    "  CASE\n"
    "    WHEN critic_rating >= 90 THEN '90-100 (elite)'\n"
    "    WHEN critic_rating >= 80 THEN '80-89 (great)'\n"
    "    WHEN critic_rating >= 70 THEN '70-79 (good)'\n"
    "    WHEN critic_rating >= 60 THEN '60-69 (mixed)'\n"
    "    WHEN critic_rating >= 50 THEN '50-59 (weak)'\n"
    "    ELSE 'below 50 (bad)'\n"
    "  END AS band,\n"
    "  COUNT(*) AS n_games,\n"
    "  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct\n"
    "FROM chart_critic_all\n"
    "GROUP BY band ORDER BY MIN(critic_rating) DESC\n"
    "''').df()"
))

cells.append(new_markdown_cell(
    "---\n"
    "## Framing to confirm\n"
    "\n"
    "1. **Hero histogram** (Chart 1) — full 0–100, 90+ in aqua, median gold. Good?\n"
    "2. **90+ per year line** (Chart 2) — cutoff year + caption OK?\n"
    "3. **User-vs-critic scatter** (Chart 3) — worth publishing? (Check the r value "
    "and whether the cloud tells a story — e.g. users rating high-critic games lower, "
    "or a tight agreement.)\n"
    "\n"
    "Once confirmed, I'll build the finalized social + web renders in `06-viz-social`."
))

cells.append(new_markdown_cell(
    "---\n"
    "## Cleanup\n"
    "Close the (read-only) DuckDB connection so the lock is released."
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

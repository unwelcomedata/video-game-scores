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
    "    title='Video game critic review scores',\n"
    "    subtitle='Distribution of IGDB critic ratings \u2014 6,005 games (\u2265 3 critic scores each); each bar = a 5-point band. 90+ highlighted.',\n"
    "    source='IGDB',\n"
    ")\n"
    "display(img)"
))

cells.append(new_markdown_cell(
    "## Chart 1b (HERO, user side) — distribution of IGDB USER ratings\n"
    "\n"
    "The same histogram treatment applied to the **community/user** rating instead of "
    "the critic aggregate — the natural companion to the hero, and **same colors** "
    "(teal bars, aqua 90+ band) so the pair reads as one set; the title carries the "
    "critic-vs-user distinction. Same 5-point bands and full 0\u2013100 range, so the two "
    "are directly comparable. Users draw from a different pool of games (only those "
    "with a user rating), so the count and shape differ from the critic histogram \u2014 "
    "the interesting question is whether users pile up in the same 70s\u201380s or spread "
    "wider/lower."
))

cells.append(new_code_cell(
    "df_user = df_all[df_all['user_rating'].notna()]\n"
    "print('games with a user rating:', len(df_user))\n"
    "print(df_user['user_rating'].describe().round(1).to_string())\n"
    "img = histogram(\n"
    "    df_user, value_col='user_rating',\n"
    "    bin_edges=list(range(0, 101, 5)), x_range=(0, 100), x_tick_step=10,\n"
    "    x_axis_label='IGDB user rating', y_axis_label='Number of games',\n"
    "    bar_color=c('teal'), highlight_range=(90, 100, c('aqua')),\n"
    "    title='Video game user review scores',\n"
    "    subtitle=f'Distribution of IGDB user ratings \u2014 {len(df_user):,} games with a community rating; each bar = a 5-point band. 90+ highlighted.',\n"
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
    "## Chart 2b — average critic vs average user rating by year (two lines)\n"
    "\n"
    "One line for the mean **critic** rating and one for the mean **user** rating, per "
    "release year \u2014 do the two audiences track each other over time, and is one "
    "consistently higher? Averages are computed inline from `chart_critic_all` "
    "(exploration; if this chart is kept, its series get a proper `chart_` table in "
    "`03-prepare` before `06-viz-social`). Restricted to years with enough scored "
    "games to be stable, and cut at the same last-complete year as the 90+ line so "
    "recent partial years don't distort the tail. User means only cover games that "
    "have a user rating."
))

cells.append(new_code_cell(
    "avg_by_year = con.execute(f'''\n"
    "  SELECT release_year AS year,\n"
    "         ROUND(AVG(critic_rating), 1) AS avg_critic,\n"
    "         ROUND(AVG(user_rating), 1)   AS avg_user,\n"
    "         COUNT(*) AS n_games\n"
    "  FROM chart_critic_all\n"
    "  WHERE release_year IS NOT NULL\n"
    "  GROUP BY release_year\n"
    "  HAVING COUNT(*) >= 10 AND release_year <= {cut}\n"
    "  ORDER BY release_year\n"
    "''').df()\n"
    "print('spans', int(avg_by_year['year'].min()), '\u2192', int(avg_by_year['year'].max()))\n"
    "print(avg_by_year.to_string(index=False))\n"
    "img = line_chart(\n"
    "    avg_by_year, x_col='year',\n"
    "    series=[\n"
    "        {'col': 'avg_critic', 'label': 'Critic', 'color': c('teal')},\n"
    "        {'col': 'avg_user',   'label': 'User',   'color': c('caramel')},\n"
    "    ],\n"
    "    x_axis_label='Release year', y_axis_label='Average rating (0\u2013100)',\n"
    "    y_min=60, y_max=90, markers=True, label_last=True,\n"
    "    title='Video game review scores \u2014 average critic vs user rating by year',\n"
    "    subtitle=f'IGDB ratings, mean per release year. Years with \u2265 10 scored games, through {cut}.',\n"
    "    source='IGDB',\n"
    ")\n"
    "display(img)"
))

cells.append(new_markdown_cell(
    "## Chart 3 — user rating vs critic rating (outliers labelled)\n"
    "\n"
    "Do IGDB users agree with critics? Point per game (the ~5,300 with both a critic "
    "and a user rating), with a dashed **y = x** agreement line. The **outliers** \u2014 "
    "the games that stand most alone on the plot \u2014 are coloured a warm **rust** "
    "(spice) and labelled with the game name over a white pill so the text reads over "
    "the point cloud; everything else stays teal. \"Outlier\" here = the most "
    "**visually isolated** points: for each game we measure the mean distance to its "
    "8 nearest neighbours in normalized score space, and label the 12 with the most "
    "empty space around them. That matches what the eye reads as \u2018standing out\u2019 \u2014 it "
    "catches the lonely dots in every corner (sparse upper-left, lower-left, and the "
    "odd straggler) and, unlike a distance-from-the-trend measure, does NOT over-pick "
    "the tightly-packed cluster in the lower-right where the points have close "
    "neighbours.\n"
    "\n"
    "*One row is dropped: **Infernal** has a critic rating of 0.0 \u201cbacked by\u201d 6 "
    "outlets \u2014 an aggregate of exactly zero over 6 critics is not a real mean, it's "
    "an IGDB data gap (it would otherwise be the most isolated dot of all), so it's "
    "filtered out of the scatter rather than labelled.*"
))

cells.append(new_code_cell(
    "df_scatter = con.execute('''\n"
    "  SELECT name, critic_rating, user_rating\n"
    "  FROM chart_critic_all\n"
    "  WHERE user_rating IS NOT NULL\n"
    "    AND critic_rating > 0   -- drop the single critic=0 artifact (Infernal:\n"
    "                            -- aggregate 0.0 over 6 outlets is not a real mean;\n"
    "                            -- it's an IGDB gap, and it reads as a lonely far-left dot)\n"
    "''').df()\n"
    "print('games with both ratings (critic>0):', len(df_scatter))\n"
    "corr = df_scatter['critic_rating'].corr(df_scatter['user_rating'])\n"
    "print('Pearson r:', round(corr, 3))\n"
    "\n"
    "# Outliers = the most VISUALLY ISOLATED points \u2014 the ones with the most empty\n"
    "# space around them, which is what the eye actually reads as \u2018standing out\u2019.\n"
    "# Measure: mean distance to each point's K nearest neighbours in normalized\n"
    "# (0\u20131 per axis) score space, so both axes weigh equally and 'isolation' means\n"
    "# the same thing everywhere on the plot. Dense-cloud points have tiny neighbour\n"
    "# distances; a lonely dot in open space has a large one. This flags the sparse\n"
    "# corners in EVERY region (upper-left, lower-left, lone stragglers) and does NOT\n"
    "# over-pick the tightly-packed lower-right cluster, unlike the residual metric.\n"
    "import numpy as np\n"
    "N_OUTLIERS = 12\n"
    "K = 8\n"
    "cx = df_scatter['critic_rating'].values.astype(float)\n"
    "uy = df_scatter['user_rating'].values.astype(float)\n"
    "nx = (cx - cx.min()) / (cx.max() - cx.min())\n"
    "ny = (uy - uy.min()) / (uy.max() - uy.min())\n"
    "P = np.column_stack([nx, ny])\n"
    "n = len(P)\n"
    "iso = np.empty(n)\n"
    "for i in range(0, n, 500):                     # chunked brute-force kNN (no scipy)\n"
    "    blk = P[i:i+500]\n"
    "    d2 = ((blk[:, None, :] - P[None, :, :]) ** 2).sum(2)\n"
    "    d2.sort(axis=1)\n"
    "    iso[i:i+500] = np.sqrt(d2[:, 1:K+1]).mean(1)  # skip self (col 0)\n"
    "df_scatter['isolation'] = iso\n"
    "outlier_idx = df_scatter['isolation'].nlargest(N_OUTLIERS).index\n"
    "df_scatter['is_outlier'] = df_scatter.index.isin(outlier_idx)\n"
    "print(f'\\nlabelled outliers (most isolated \u2014 mean dist to {K} nearest neighbours):')\n"
    "print(df_scatter.loc[outlier_idx, ['name','critic_rating','user_rating','isolation']]\n"
    "      .reindex(df_scatter.loc[outlier_idx,'isolation'].sort_values(ascending=False).index)\n"
    "      .round(3).to_string(index=False))\n"
    "\n"
    "img = scatter_plot(\n"
    "    df_scatter, x_col='critic_rating', y_col='user_rating',\n"
    "    x_axis_label='IGDB critic rating', y_axis_label='IGDB user rating',\n"
    "    point_color=c('teal'),\n"
    "    label_col='name', outlier_col='is_outlier',\n"
    "    outlier_color=c('spice'), label_outliers_only=True,\n"
    "    ref_lines=[{'kind': 'diagonal', 'color': c('gray'), 'label': 'users = critics'}],\n"
    "    title='Video game review scores \u2014 IGDB user rating vs critic rating',\n"
    "    subtitle=f'{len(df_scatter):,} games with both ratings (0\u2013100). Pearson r = {corr:.2f}. Highlighted = the {N_OUTLIERS} most isolated games (most empty space around them).',\n"
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
    "## Status\n"
    "\n"
    "**Confirmed for social** (owner, this session):\n"
    "- **Video game critic review scores** (Chart 1) — histogram, teal bars, aqua 90+.\n"
    "- **Video game user review scores** (Chart 1b) — histogram, **same colors**, "
    "distinction carried in the title.\n"
    "- **Avg critic vs user by year** (Chart 2b) — the two-line chart (critic + user).\n"
    "- **User-vs-critic scatter** (Chart 3) — outliers coloured navy + labelled with the "
    "game name.\n"
    "\n"
    "Still open / not part of the social set: the **90+ per year line** (Chart 2) — kept "
    "here for reference, not confirmed for publication.\n"
    "\n"
    "Next: build the finalized social + web renders in `06-viz-social` for the four "
    "confirmed charts (and add a `chart_avg_by_year` + scatter/outlier `chart_` table in "
    "`03-prepare` so the social renders read from the DB, not inline queries)."
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

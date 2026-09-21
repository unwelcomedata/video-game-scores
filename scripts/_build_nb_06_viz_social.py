"""Build notebooks/06-viz-social.ipynb — publication charts (IGDB video game scores).

The owner reviewed 04-viz and confirmed the framing, so this renders the
publication-ready set. Four charts, each in TWO targets from the same chart_ table:
  - SOCIAL: full chrome (title/subtitle/source/watermark), twitter_landscape 1600x900
            -> outputs/social/
  - WEB:    web_mode=True (drops title/subtitle/source, watermark only), web 1664x936
            -> outputs/web/  (embedded on the Pages site, which supplies headings)

The four confirmed charts:
  1. Video game critic review scores  — histogram of IGDB critic ratings (hero)
  2. Video game user review scores    — histogram of IGDB user ratings (same colors)
  3. Average critic vs user by year   — two-line (critic + user)
  4. IGDB user vs critic rating       — scatter, 12 most-isolated games labelled (rust)

    .venv/bin/python scripts/_build_nb_06_viz_social.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

PROJECT = Path(__file__).resolve().parent.parent
NB = PROJECT / "notebooks" / "06-viz-social.ipynb"

cells = []

cells.append(new_markdown_cell(
    "# 06 — Social (publication charts)\n"
    "\n"
    "The owner reviewed `04-viz` and confirmed the framing, so this notebook renders "
    "the publication-ready set. Four charts, each in **two targets** from the same "
    "`chart_` tables:\n"
    "- **Social** — full chrome (title, subtitle, source, watermark), "
    "`twitter_landscape` (1600×900) → `outputs/social/`.\n"
    "- **Web** — `web_mode=True` (drops title/subtitle/source, keeps only the "
    "`@unwelcomedata` watermark), `web` preset (1664×936) → `outputs/web/`. These get "
    "embedded on the Pages site, which supplies its own headings.\n"
    "\n"
    "**The four charts (confirmed in `04-viz`):**\n"
    "1. **Video game critic review scores** — distribution of IGDB critic ratings "
    "(hero); teal bars, 90+ band aqua.\n"
    "2. **Video game user review scores** — distribution of IGDB user ratings; **same "
    "colours**, the critic-vs-user distinction is carried in the title.\n"
    "3. **Average critic vs user rating by year** — two lines (critic teal, user "
    "caramel).\n"
    "4. **IGDB user rating vs critic rating** — scatter; the 12 most visually-isolated "
    "games coloured rust and labelled.\n"
    "\n"
    "⚠️ **Web info-preservation:** web mode drops the title/subtitle/source, so any "
    "fact living ONLY there must be restated in the Pages README above each chart:\n"
    "- Charts 1 & 2 differ ONLY by **critic vs user** (title) — in web mode the two "
    "histograms look near-identical, so each needs its own labelled heading. (The "
    "x-axis labels \u201cIGDB critic rating\u201d / \u201cIGDB user rating\u201d do survive in-image.)\n"
    "- Chart 3: the metric (**mean rating per year**), the year range, and the ≥10-games "
    "filter live in the subtitle → restate above the chart. The **Critic/User** line "
    "end-labels survive in-image.\n"
    "- Chart 4: **what \u2018outlier\u2019 means** (most isolated), the r value, and the dropped "
    "critic=0 row live in the subtitle → restate. Axis labels + point labels survive.\n"
    "\n"
    "*Titles are **descriptive** (house default). Source = IGDB. Read-only DuckDB; "
    "closed in the Cleanup cell.*"
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
    "sys.path.insert(0, str(PROJECT.parent.parent / 'shared'))\n"
    "\n"
    "import duckdb\n"
    "from IPython.display import display\n"
    "from src.ingest import load_config\n"
    "from colors import c\n"
    "from chart_templates import histogram, line_chart, scatter_plot\n"
    "from viz import PRESETS\n"
    "\n"
    "cfg = load_config('config.yaml')\n"
    "con = duckdb.connect(cfg['settings']['duckdb_file'], read_only=True)\n"
    "soc_w, soc_h, _ = PRESETS['twitter_landscape']   # 1600 x 900\n"
    "web_w, web_h, _ = PRESETS['web']                 # 1664 x 936\n"
    "social_out = Path(cfg['paths']['outputs_social']); social_out.mkdir(parents=True, exist_ok=True)\n"
    "web_out = social_out.parent / 'web'; web_out.mkdir(parents=True, exist_ok=True)\n"
    "SRC = 'IGDB (Internet Game Database) API'\n"
    "print('presets  social', (soc_w, soc_h), ' web', (web_w, web_h))"
))

# ── Chart 1: critic histogram ────────────────────────────────────────────────
cells.append(new_markdown_cell(
    "## Chart 1 (hero) — Video game critic review scores\n"
    "\n"
    "Distribution of IGDB critic ratings across the 6,005 games with ≥ 3 critic "
    "scores. 5-point bands, mean + median reference lines, 90+ club highlighted aqua."
))
cells.append(new_code_cell(
    "df_all = con.execute('SELECT critic_rating, user_rating FROM chart_critic_all').df()\n"
    "df_user = df_all[df_all['user_rating'].notna()]\n"
    "n_critic = len(df_all)\n"
    "\n"
    "def critic_hist(title, subtitle, source, w, h, web):\n"
    "    return histogram(\n"
    "        df_all, value_col='critic_rating',\n"
    "        bin_edges=list(range(0, 101, 5)), x_range=(0, 100), x_tick_step=10,\n"
    "        x_axis_label='IGDB critic rating', y_axis_label='Number of games',\n"
    "        bar_color=c('teal'), highlight_range=(90, 100, c('aqua')),\n"
    "        title=title, subtitle=subtitle, source=source,\n"
    "        img_width=w, img_height=h, web_mode=web)\n"
    "\n"
    "img = critic_hist(\n"
    "    'Video game critic review scores',\n"
    "    f'Distribution of IGDB critic ratings \u2014 {n_critic:,} games (\u2265 3 critic scores each); each bar = a 5-point band. 90+ highlighted.',\n"
    "    SRC, soc_w, soc_h, False)\n"
    "img.save(social_out / '01_critic_score_distribution.png'); display(img)\n"
    "critic_hist('', None, None, web_w, web_h, True).save(web_out / '01_critic_score_distribution.png')\n"
    "print('saved 01 (social + web)')"
))

# ── Chart 2: user histogram ──────────────────────────────────────────────────
cells.append(new_markdown_cell(
    "## Chart 2 — Video game user review scores\n"
    "\n"
    "The same histogram treatment for the community/user rating — **same colours** as "
    "the critic hero so the pair reads as one set; the distinction is in the title. "
    "Fewer games (only those with a user rating)."
))
cells.append(new_code_cell(
    "n_user = len(df_user)\n"
    "\n"
    "def user_hist(title, subtitle, source, w, h, web):\n"
    "    return histogram(\n"
    "        df_user, value_col='user_rating',\n"
    "        bin_edges=list(range(0, 101, 5)), x_range=(0, 100), x_tick_step=10,\n"
    "        x_axis_label='IGDB user rating', y_axis_label='Number of games',\n"
    "        bar_color=c('teal'), highlight_range=(90, 100, c('aqua')),\n"
    "        title=title, subtitle=subtitle, source=source,\n"
    "        img_width=w, img_height=h, web_mode=web)\n"
    "\n"
    "img = user_hist(\n"
    "    'Video game user review scores',\n"
    "    f'Distribution of IGDB user ratings \u2014 {n_user:,} games with a community rating; each bar = a 5-point band. 90+ highlighted.',\n"
    "    SRC, soc_w, soc_h, False)\n"
    "img.save(social_out / '02_user_score_distribution.png'); display(img)\n"
    "user_hist('', None, None, web_w, web_h, True).save(web_out / '02_user_score_distribution.png')\n"
    "print('saved 02 (social + web)')"
))

# ── Chart 3: avg critic vs user by year (two lines) ──────────────────────────
cells.append(new_markdown_cell(
    "## Chart 3 — Average critic vs user rating by year\n"
    "\n"
    "One line for the mean **critic** rating, one for the mean **user** rating, per "
    "release year (from `chart_avg_by_year`: years with ≥ 10 scored games, cut at the "
    "last complete year). The lines cross around 2010–11 — users rated higher in the "
    "2000s, critics pull ahead in the 2010s."
))
cells.append(new_code_cell(
    "avg = con.execute('SELECT year, avg_critic, avg_user FROM chart_avg_by_year ORDER BY year').df()\n"
    "yr_lo, yr_hi = int(avg['year'].min()), int(avg['year'].max())\n"
    "\n"
    "def year_line(title, subtitle, source, w, h, web):\n"
    "    return line_chart(\n"
    "        avg, x_col='year',\n"
    "        series=[{'col': 'avg_critic', 'label': 'Critic', 'color': c('teal')},\n"
    "                {'col': 'avg_user',   'label': 'User',   'color': c('caramel')}],\n"
    "        x_axis_label='Release year', y_axis_label='Average rating (0\u2013100)',\n"
    "        y_min=60, y_max=90, markers=True, label_last=True,\n"
    "        title=title, subtitle=subtitle, source=source,\n"
    "        img_width=w, img_height=h, web_mode=web)\n"
    "\n"
    "img = year_line(\n"
    "    'Video game review scores \u2014 average critic vs user rating by year',\n"
    "    f'IGDB ratings, mean per release year ({yr_lo}\u2013{yr_hi}). Years with \u2265 10 scored games.',\n"
    "    SRC, soc_w, soc_h, False)\n"
    "img.save(social_out / '03_avg_rating_by_year.png'); display(img)\n"
    "year_line('', None, None, web_w, web_h, True).save(web_out / '03_avg_rating_by_year.png')\n"
    "print('saved 03 (social + web)')"
))

# ── Chart 4: scatter with isolation outliers ─────────────────────────────────
cells.append(new_markdown_cell(
    "## Chart 4 — IGDB user rating vs critic rating (outliers labelled)\n"
    "\n"
    "Point per game (from `chart_scatter`: both ratings, critic > 0). A dashed y = x "
    "agreement line; the 12 most **visually isolated** games (most empty space around "
    "them, by nearest-neighbour distance) are coloured rust and labelled. The `is_outlier` "
    "flag and the outlier definition are baked into `03-prepare`, so this reads straight "
    "from the table."
))
cells.append(new_code_cell(
    "sc = con.execute('SELECT name, critic_rating, user_rating, is_outlier FROM chart_scatter').df()\n"
    "corr = sc['critic_rating'].corr(sc['user_rating'])\n"
    "n_out = int(sc['is_outlier'].sum())\n"
    "\n"
    "def rating_scatter(title, subtitle, source, w, h, web):\n"
    "    return scatter_plot(\n"
    "        sc, x_col='critic_rating', y_col='user_rating',\n"
    "        x_axis_label='IGDB critic rating', y_axis_label='IGDB user rating',\n"
    "        point_color=c('teal'),\n"
    "        label_col='name', outlier_col='is_outlier',\n"
    "        outlier_color=c('spice'), label_outliers_only=True,\n"
    "        ref_lines=[{'kind': 'diagonal', 'color': c('gray'), 'label': 'users = critics'}],\n"
    "        title=title, subtitle=subtitle, source=source,\n"
    "        img_width=w, img_height=h, web_mode=web)\n"
    "\n"
    "img = rating_scatter(\n"
    "    'Video game review scores \u2014 IGDB user rating vs critic rating',\n"
    "    f'{len(sc):,} games with both ratings (0\u2013100). Pearson r = {corr:.2f}. Highlighted = the {n_out} most isolated games (most empty space around them).',\n"
    "    SRC, soc_w, soc_h, False)\n"
    "img.save(social_out / '04_user_vs_critic_scatter.png'); display(img)\n"
    "rating_scatter('', None, None, web_w, web_h, True).save(web_out / '04_user_vs_critic_scatter.png')\n"
    "print('saved 04 (social + web)')"
))

cells.append(new_markdown_cell(
    "---\n"
    "**Next:** run `scripts/validate_charts.py` (must exit 0) — it re-derives every "
    "chart's facts from DuckDB, checks the export matches, and confirms social/web "
    "parity. Then the project is ready for the independent validation pass and "
    "fun-tier release curation (`public-release.md`)."
))

cells.append(new_markdown_cell(
    "---\n## Cleanup\nClose the read-only DuckDB connection so the lock is released."
))
cells.append(new_code_cell("con.close()\nprint('connection closed')"))

nb = new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.14"},
})
NB.write_text(nbf.writes(nb), encoding="utf-8")
print(f"wrote {NB}")

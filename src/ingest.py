"""Web ingestion utilities.

Handles three source types:
  - html_table  : pandas read_html on a static page
  - html_scrape : BeautifulSoup for custom element extraction
  - csv / json  : direct download and save to data/raw

All raw files land in data/raw unchanged. Call load_config() once per notebook
to get paths and source definitions from config.yaml.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_config(config_path: str | Path = "config.yaml") -> dict[str, Any]:
    """Load project config.yaml and return it as a dict."""
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def raw_path(cfg: dict, filename: str) -> Path:
    """Return a Path inside data/raw, creating the directory if needed."""
    p = Path(cfg["paths"]["data_raw"]) / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_CACHE_DIR: Path | None = None


def _get_cache_dir(cfg: dict) -> Path:
    """Return the cache directory (data/raw by default)."""
    global _CACHE_DIR
    if _CACHE_DIR is None:
        _CACHE_DIR = Path(cfg["paths"]["data_raw"])
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


def fetch_html(url: str, headers: dict | None = None, timeout: int = 30) -> str:
    """Fetch a URL and return the response text.

    Raises requests.HTTPError on non-2xx status.
    """
    hdrs = {**_DEFAULT_HEADERS, **(headers or {})}
    resp = requests.get(url, headers=hdrs, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def fetch_cached(
    url: str,
    filename: str,
    cfg: dict,
    max_age_hours: float = 24.0,
    headers: dict | None = None,
    timeout: int = 30,
) -> str:
    """Fetch a URL with local file caching.

    If a cached file exists and is younger than max_age_hours, returns its
    contents without making a network request. Otherwise fetches, saves to
    data/raw/{filename}, and returns the content.

    Args:
        url:            URL to fetch.
        filename:       Cache filename (saved in data/raw/).
        cfg:            Loaded config dict.
        max_age_hours:  Re-fetch if cache is older than this (0 = always fetch).
        headers:        Optional extra HTTP headers.
        timeout:        Request timeout in seconds.

    Returns:
        Response text (from cache or network).
    """
    cache_path = _get_cache_dir(cfg) / filename
    if cache_path.exists() and max_age_hours > 0:
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        if age_hours < max_age_hours:
            return cache_path.read_text(encoding="utf-8")

    text = fetch_html(url, headers=headers, timeout=timeout)
    cache_path.write_text(text, encoding="utf-8")
    return text


def fetch_with_retry(
    url: str,
    headers: dict | None = None,
    timeout: int = 30,
    max_retries: int = 3,
    rate_limit_seconds: float = 1.5,
) -> str:
    """Fetch a URL with rate limiting and exponential backoff on 429s.

    Args:
        url:                 URL to fetch.
        headers:             Optional extra HTTP headers.
        timeout:             Request timeout in seconds.
        max_retries:         Max retry attempts on 429/5xx.
        rate_limit_seconds:  Minimum delay between requests.

    Returns:
        Response text.

    Raises:
        requests.HTTPError after exhausting retries.
    """
    hdrs = {**_DEFAULT_HEADERS, **(headers or {})}
    time.sleep(rate_limit_seconds)

    for attempt in range(max_retries + 1):
        resp = requests.get(url, headers=hdrs, timeout=timeout)
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt < max_retries:
                wait = rate_limit_seconds * (2 ** attempt)
                print(f"  ⚠ {resp.status_code} on {url} — retrying in {wait:.0f}s")
                time.sleep(wait)
                continue
        resp.raise_for_status()
        return resp.text

    resp.raise_for_status()  # will raise on the last failed attempt
    return ""  # unreachable


def fetch_html_js(url: str, wait_selector: str | None = None, timeout: int = 30000) -> str:
    """Fetch a JS-rendered page using Playwright (headless Chromium).

    Use this when fetch_html() returns an empty or incomplete page.
    Requires: playwright install chromium

    Args:
        url:           Page URL.
        wait_selector: Optional CSS selector to wait for before returning HTML.
        timeout:       Playwright timeout in milliseconds.
    """
    from playwright.sync_api import sync_playwright  # lazy import

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(extra_http_headers=_DEFAULT_HEADERS)
        page.goto(url, timeout=timeout)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=timeout)
        else:
            page.wait_for_load_state("networkidle", timeout=timeout)
        html = page.content()
        browser.close()
    return html


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_html_table(html: str, table_index: int = 0) -> pd.DataFrame:
    """Extract a <table> from HTML by index and return it as a DataFrame.

    Cleans up column names: lowercase, spaces → underscores.

    Note: pandas 3.x no longer accepts a raw HTML *string* — it must be a
    file-like object — so the string is wrapped in StringIO.
    """
    from io import StringIO

    tables = pd.read_html(StringIO(html))
    if not tables:
        raise ValueError("No tables found in the provided HTML.")
    if table_index >= len(tables):
        raise IndexError(
            f"table_index {table_index} out of range — page has {len(tables)} table(s)."
        )
    df = tables[table_index]
    df.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_")
        for c in df.columns
    ]
    return df


def parse_html_scrape(
    html: str,
    row_selector: str,
    field_map: dict[str, str],
) -> pd.DataFrame:
    """Scrape structured rows from HTML using CSS selectors.

    Args:
        html:          Raw HTML string.
        row_selector:  CSS selector that matches each "row" element.
        field_map:     Dict mapping output column name → CSS selector
                       relative to each row element.
                       Use '' (empty string) to get the row's own text.

    Example:
        parse_html_scrape(html, "tr.data-row", {"name": "td.name", "value": "td.val"})
    """
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select(row_selector)
    records = []
    for row in rows:
        record: dict[str, str] = {}
        for col, selector in field_map.items():
            el = row.select_one(selector) if selector else row
            record[col] = el.get_text(" ", strip=True) if el else ""
        records.append(record)
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def download_file(url: str, dest: Path, headers: dict | None = None, timeout: int = 60) -> Path:
    """Stream-download a file (CSV, JSON, zip, etc.) to dest and return the path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    hdrs = {**_DEFAULT_HEADERS, **(headers or {})}
    with requests.get(url, headers=hdrs, timeout=timeout, stream=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
    return dest


# ---------------------------------------------------------------------------
# Source-driven ingest (reads config.yaml sources block)
# ---------------------------------------------------------------------------

def ingest_source(
    name: str,
    cfg: dict,
    save_raw: bool = True,
    js_wait_selector: str | None = None,
    row_selector: str | None = None,
    field_map: dict[str, str] | None = None,
    rate_limit_seconds: float = 1.0,
) -> pd.DataFrame:
    """Ingest a named source from config.yaml and return a DataFrame.

    Args:
        name:               Key under `sources:` in config.yaml.
        cfg:                Loaded config dict (from load_config()).
        save_raw:           If True, save the raw HTML/bytes to data/raw/.
        js_wait_selector:   Passed to fetch_html_js() if js_render is true.
        row_selector:       Required for html_scrape type.
        field_map:          Required for html_scrape type.
        rate_limit_seconds: Polite delay before fetching.
    """
    source = cfg["sources"][name]
    url: str = source["url"]
    source_type: str = source.get("type", "html_table")
    js_render: bool = source.get("js_render", False)
    table_index: int = source.get("table_index", 0)

    time.sleep(rate_limit_seconds)

    if source_type == "csv":
        dest = raw_path(cfg, f"{name}.csv")
        download_file(url, dest)
        return pd.read_csv(dest, encoding=cfg["settings"]["encoding"])

    if source_type == "json":
        dest = raw_path(cfg, f"{name}.json")
        download_file(url, dest)
        with open(dest, encoding=cfg["settings"]["encoding"]) as f:
            data = json.load(f)
        return pd.json_normalize(data)

    # HTML-based types
    html = fetch_html_js(url, wait_selector=js_wait_selector) if js_render else fetch_html(url)

    if save_raw:
        raw_path(cfg, f"{name}.html").write_text(html, encoding="utf-8")

    if source_type == "html_table":
        return parse_html_table(html, table_index=table_index)

    if source_type == "html_scrape":
        if row_selector is None or field_map is None:
            raise ValueError("html_scrape requires row_selector and field_map arguments.")
        return parse_html_scrape(html, row_selector, field_map)

    raise ValueError(f"Unknown source type '{source_type}'. Use: html_table, html_scrape, csv, json.")


# ---------------------------------------------------------------------------
# IGDB API ingest (generic, config-driven, secrets passed in — never hardcoded)
# ---------------------------------------------------------------------------

def igdb_access_token(client_id: str, client_secret: str, cfg: dict) -> str:
    """Exchange Twitch app credentials for a short-lived IGDB OAuth token.

    IGDB auth runs through Twitch's client-credentials flow. The returned bearer
    token is used in the ``Authorization`` header on every IGDB request. Secrets
    are passed in by the caller (read from the gitignored ``.env``), never stored
    or logged here.
    """
    token_url = cfg["sources"]["igdb_games"].get(
        "token_url", "https://id.twitch.tv/oauth2/token"
    )
    resp = requests.post(token_url, params={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _igdb_id_name_map(
    endpoint: str, ids: list[int], client_id: str, token: str, cfg: dict,
) -> dict[int, str]:
    """Fetch id→name for a reference endpoint (e.g. genres, platforms).

    IGDB stores genres/platforms as ID arrays on each game; this resolves them to
    names in bulk so the games table can carry readable, comma-joined strings.
    """
    if not ids:
        return {}
    base = cfg["sources"]["igdb_games"]["base_url"].rsplit("/", 1)[0]
    headers = {"Client-ID": client_id, "Authorization": f"Bearer {token}",
               "Accept": "application/json"}
    out: dict[int, str] = {}
    uniq = sorted(set(int(i) for i in ids))
    for start in range(0, len(uniq), 500):
        chunk = uniq[start:start + 500]
        id_list = ",".join(str(i) for i in chunk)
        body = f"fields id,name; where id = ({id_list}); limit 500;"
        resp = requests.post(f"{base}/{endpoint}", data=body, headers=headers, timeout=30)
        resp.raise_for_status()
        for row in resp.json():
            out[row["id"]] = row.get("name", "")
        time.sleep(cfg["sources"]["igdb_games"].get("rate_limit_seconds", 0.3))
    return out


def fetch_igdb_games(
    client_id: str,
    token: str,
    cfg: dict,
    *,
    min_aggregated_rating_count: int | None = None,
    max_pages: int | None = None,
    save_raw: bool = True,
    verbose: bool = True,
) -> pd.DataFrame:
    """Page through the IGDB /games endpoint and return one row per game.

    Generic and config-driven: endpoint, page size (IGDB max 500), rate limit and
    the critic-count floor all come from ``cfg['sources']['igdb_games']``. The
    OAuth token + client id are passed in (from .env via igdb_access_token), never
    hardcoded or logged.

    IGDB uses POST with an Apicalypse query body and offset paging. We request all
    games that have a critic aggregate backed by at least
    ``min_aggregated_rating_count`` outlets, then resolve genre/platform IDs to
    names in bulk. ``first_release_date`` is a unix timestamp → we derive
    ``release_year``.

    Returns a DataFrame with columns: id, slug, name, release_year,
    aggregated_rating (critic 0-100), aggregated_rating_count, rating (user 0-100),
    rating_count, total_rating, total_rating_count, genre_ids, platform_ids.
    (Genre/platform NAMES are joined on in the notebook via _igdb_id_name_map.)
    """
    src = cfg["sources"]["igdb_games"]
    base_url: str = src["base_url"]
    page_size: int = min(int(src.get("page_size", 500)), 500)
    rate_limit: float = float(src.get("rate_limit_seconds", 0.3))
    if min_aggregated_rating_count is None:
        min_aggregated_rating_count = int(src.get("min_aggregated_rating_count", 3))

    headers = {"Client-ID": client_id, "Authorization": f"Bearer {token}",
               "Accept": "application/json"}
    fields = ("id,slug,name,first_release_date,aggregated_rating,"
              "aggregated_rating_count,rating,rating_count,total_rating,"
              "total_rating_count,genres,platforms")
    where = f"aggregated_rating != null & aggregated_rating_count >= {min_aggregated_rating_count}"

    raw_dir = Path(cfg["paths"]["data_raw"]) / "igdb"
    if save_raw:
        raw_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    offset = 0
    page = 0
    while True:
        page += 1
        if max_pages is not None and page > max_pages:
            break
        body = (f"fields {fields}; where {where}; "
                f"sort aggregated_rating desc; limit {page_size}; offset {offset};")
        time.sleep(rate_limit)
        resp = requests.post(base_url, data=body, headers=headers, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break

        if save_raw:
            (raw_dir / f"page_{page:04d}.json").write_text(
                json.dumps(batch), encoding="utf-8"
            )

        for g in batch:
            ts = g.get("first_release_date")
            year = None
            if ts:
                from datetime import datetime, timezone
                year = datetime.fromtimestamp(ts, tz=timezone.utc).year
            records.append({
                "id": g.get("id"),
                "slug": g.get("slug"),
                "name": g.get("name"),
                "release_year": year,
                "aggregated_rating": g.get("aggregated_rating"),        # critic 0-100
                "aggregated_rating_count": g.get("aggregated_rating_count"),
                "rating": g.get("rating"),                              # user 0-100
                "rating_count": g.get("rating_count"),
                "total_rating": g.get("total_rating"),
                "total_rating_count": g.get("total_rating_count"),
                "genre_ids": g.get("genres") or [],
                "platform_ids": g.get("platforms") or [],
            })

        if verbose and page % 5 == 0:
            print(f"  page {page} — {len(records):,} games so far")

        offset += page_size
        if len(batch) < page_size:
            break

    if verbose:
        print(f"Done: {len(records):,} games across {page} page(s)")
    return pd.DataFrame.from_records(records)

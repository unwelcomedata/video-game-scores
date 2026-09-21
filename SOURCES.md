# Data Sources — video-game-scores

Source standards are **tiered**:
- **Serious tier** (methodology invites scrutiny): use official government or
  authoritative primary sources only. Crowd-edited references (Wikipedia, etc.)
  are NOT used — credibility is the product.
- **Fun tier** (low-stakes pop-culture): crowd-sourced references (fan wikis,
  SuperSummary, etc.) and owner-as-primary (hand-collected counts from a book or
  broadcast) are fine — just cite them plainly below.

Document every data source here before ingesting it. Include enough detail
that someone else could independently locate and verify the original data.

---

## Source Template

Copy and fill in for each source. The **How the source collects the data**,
**How the source defines the data**, and **Methodology changes / series breaks**
sections are required — they are what keep our analysis honest and prevent
apples-to-oranges comparisons. Do not leave them blank; if something is genuinely
not applicable or unknown, write "N/A" or "unknown" so it's clear it was considered.

### [Source Name]
- **Publisher:** [Agency, organization, or author]
- **URL:** [Direct link to the file or page]
- **Format:** [CSV | JSON | HTML table | ZIP | PDF | hand-curated]
- **License:** [Public domain | CC0 | CC-BY | proprietary | etc.]
- **Fields used:** [Column names or description of what was extracted]
- **Coverage:** [Geographic scope, date range, or other relevant bounds]
- **How the source collects the data:** [How does the publisher actually gather it?
  Survey / administrative records / registration / model estimate / scraped, etc.
  For surveys: sampling frame, sample size, response rate. For counts: the universe
  and denominator. Who is included and who is excluded from the raw collection?]
- **How the source defines the data:** [How is the thing being measured *defined*?
  Spell out the judgment calls in what counts. Example: a "COVID death" can mean died
  *from* COVID (underlying cause) vs. died *with* COVID (contributing/any mention) —
  very different counts. Note the exact definition this source uses.]
- **Methodology changes / series breaks:** [Dates when the definition or collection
  method changed, and which time periods are therefore NOT directly comparable.
  If the whole series is consistent, say so explicitly. This is the flag that stops
  us from charting a pre-change number next to a post-change number as if they match.]
- **Known controversies / debates:** [Any contested measurement choices worth a
  footnote or caveat in a published chart. Optional but encouraged. "None known" is
  a valid answer once you've checked.]
- **Notes:** [Anything else — data-quality quirks, suppression rules, imputation, etc.]
- **Retrieved:** [YYYY-MM-DD]

---

## Sources

### IGDB — Internet Game Database (API)
- **Publisher:** IGDB, owned by Twitch (Amazon). A large, actively-maintained video-game database.
- **URL:** https://api.igdb.com/v4/games (docs: https://api-docs.igdb.com/). Auth via Twitch OAuth: https://id.twitch.tv/oauth2/token
- **Format:** v4 REST API (POST with an Apicalypse query body; offset-paged). Queried, not scraped.
- **License:** Free for **non-commercial** use under the Twitch Developer Services
  Agreement; attribution to IGDB. Fun-tier pop-culture project — a community/industry
  database is appropriate and cited plainly here.
- **Fields used:** `id`, `name`, `slug`, `first_release_date` (unix → release_year),
  `aggregated_rating` (external CRITIC aggregate, 0–100), `aggregated_rating_count`,
  `rating` (IGDB USER rating, 0–100), `rating_count`, `total_rating`,
  `total_rating_count`, `genres`, `platforms`.
- **Coverage:** IGDB catalogs hundreds of thousands of titles across all platforms
  and eras and syncs critic aggregates for **current** releases far better than
  Metacritic-via-RAWG (the reason this project switched sources). We keep games with a
  critic aggregate backed by **≥ 3 critic scores** (`aggregated_rating_count ≥ 3`) so
  a single stray review doesn't create a noisy "aggregate." Threshold set in `01-ingest`.
- **How the source collects the data:** IGDB aggregates metadata from the industry and
  community. `aggregated_rating` is IGDB's **own** average of external professional
  critic scores it has collected (0–100); `rating` is IGDB's **own** community/user
  rating (0–100). These are two separate measures on the same 0–100 scale — a critic
  aggregate and a user aggregate — and are NOT blended in this project (`total_rating`
  is IGDB's blend and is kept only for reference).
- **How the source defines the data:** `aggregated_rating` = mean of external critic
  outlet scores IGDB has recorded for the game, normalized to 0–100, with
  `aggregated_rating_count` outlets behind it. `rating` = mean of IGDB users' own
  ratings, 0–100, with `rating_count` users behind it. Distinct from Metacritic (a
  different aggregator with a different, weighted method) — the numbers are IGDB's, not
  Metacritic's, and should be described as "IGDB critic rating," not "Metacritic."
- **Methodology changes / series breaks:** IGDB's aggregate is a **simple mean** of the
  outlets it happens to have, so coverage/among-outlet composition varies by title and
  era; a low `aggregated_rating_count` aggregate is less stable (hence the ≥3 filter).
  As with any critic aggregate, scores have drifted upward over time and the set of
  covered outlets changes — treat cross-era comparisons as directional and bin by
  period. Very recent releases may still be accruing critic scores at pull time.
- **Known controversies / debates:** Aggregation choices (which outlets, unweighted
  mean vs weighted) are debated across all aggregators; user ratings are subject to
  review-bombing. This project reports critic and user aggregates **separately** and
  never blends them, and flags the ≥3-outlet floor. Not load-bearing for a
  distribution-shape story.
- **Notes:** Requires free Twitch app credentials (`TWITCH_CLIENT_ID` +
  `TWITCH_CLIENT_SECRET` in the gitignored `.env`), exchanged for a short-lived OAuth
  token at ingest time. Raw JSON pages cached to `data/raw/igdb/`.
- **Retrieved:** 2026-09-20

---

## Notes on Data Quality

- All source files are saved verbatim to `data/raw/` and never modified.
- Discrepancies between sources should be noted here and resolved explicitly.
- **Series breaks:** whenever a source changed its definition or method mid-series,
  document the break date under that source and treat pre/post as separate series —
  never chart or aggregate across a break without a visible caveat.
- **Definitions drive comparisons:** before comparing two numbers (across years,
  places, or sources), confirm they are defined the same way. If not, say so in the
  chart, the codebook, and any social copy.

---

## Source Provenance in DuckDB

Every table in `data/project.duckdb` has a corresponding entry in the
`_sources` metadata table:

```sql
SELECT * FROM _sources;
```

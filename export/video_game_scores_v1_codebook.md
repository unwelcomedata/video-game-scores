# video-game-scores — Dataset Codebook
Generated: 2026-09-21

## Columns

### `id`
- **Type**: `int64`
- **Non-null**: 6,005 / 6,005 (100.0%)
- **Description**: IGDB internal game id (unique per game).

### `name`
- **Type**: `str`
- **Non-null**: 6,005 / 6,005 (100.0%)
- **Description**: Game title as listed on IGDB.

### `slug`
- **Type**: `str`
- **Non-null**: 6,005 / 6,005 (100.0%)
- **Description**: IGDB URL slug for the game.

### `critic_rating`
- **Type**: `float64`
- **Non-null**: 6,005 / 6,005 (100.0%)
- **Description**: IGDB aggregated CRITIC rating, 0-100 (unweighted mean of external critic outlet scores IGDB has collected). The distribution this project charts.

### `critic_count`
- **Type**: `int32`
- **Non-null**: 6,005 / 6,005 (100.0%)
- **Description**: Number of external critic scores behind critic_rating (>= 3 by construction).

### `user_rating`
- **Type**: `float64`
- **Non-null**: 5,312 / 6,005 (88.5%)
- **Description**: IGDB community/USER rating, 0-100 (a separate measure from the critic rating; not blended with it).

### `user_count`
- **Type**: `Int32`
- **Non-null**: 5,312 / 6,005 (88.5%)
- **Description**: Number of IGDB users behind user_rating (may be null if no user ratings).

### `release_year`
- **Type**: `Int32`
- **Non-null**: 6,002 / 6,005 (100.0%)
- **Description**: Year of first release, derived from the IGDB first_release_date timestamp.

### `decade`
- **Type**: `Int32`
- **Non-null**: 6,002 / 6,005 (100.0%)
- **Description**: Release decade (release_year floored to the nearest 10) — for era comparisons.

### `genres`
- **Type**: `str`
- **Non-null**: 6,005 / 6,005 (100.0%)
- **Description**: Comma-separated IGDB genres for the game.

### `platforms`
- **Type**: `str`
- **Non-null**: 6,005 / 6,005 (100.0%)
- **Description**: Comma-separated platforms the game released on (per IGDB).

## Notes

Source: IGDB — Internet Game Database (API), https://api.igdb.com/v4/games
License: Free for non-commercial use under the Twitch Developer Services Agreement; attribution to IGDB. Fun-tier pop-culture dataset.
Scope: games with a critic aggregate backed by >= 3 critic outlets (aggregated_rating_count >= 3).
Metric: critic_rating is IGDB's aggregate of external CRITIC scores (NOT Metacritic; a different aggregator/method). user_rating is IGDB's community rating. Two separate measures, never blended.
Caveat: IGDB aggregate is an unweighted mean of whatever outlets it has, so it varies by title/era; scores drift up over time; very recent titles may still be accruing critic scores.

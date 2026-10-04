# Handoff: October 2026 revival

Branch `revive-2026`, one commit per milestone, on top of `main` (last touched Jan 2025).

## Plan status

| # | Milestone | Status |
|---|-----------|--------|
| M1 | **Recover**: runs on current Dash 4 / Plotly 7 / pandas 3 / GeoPandas 1.2, Python 3.13 | Done |
| M2 | **Clean and secure**: deduplicated callbacks, validated inputs, no query injection, security headers | Done |
| M3 | **Responsive layout**: phone, tablet and desktop | Done |
| M4 | **Performance and polish**: vectorised pandas, caching, lower memory, visual cleanup, crash fixes | Done |
| M5 | **Docs and deploy config**: README, this file, `render.yaml`, `tests/smoke_test.py` | Done |
| M6 | **Republish**: merge to `main`, deploy on Render, check the live site | **Pending.** Needs the owner's go-ahead and Render dashboard access |

## How optimised are we?

Before and after numbers, measured on the same machine under the same conditions:

| Metric | Before | After |
|---|---|---|
| Server startup | 4.7 s (14–50 s with the original GitHub downloads) | **~2 s** |
| Peak memory | 787 MB (over the 512 MB Render tier) | **~350 MB** typical, 421 MB worst case |
| One interaction (slider/menu), uncached | ~1.3 s | **~0.2–0.4 s** |
| Same interaction, seen before | ~1.3 s | **near-instant** (LRU cache) |
| Page ready in browser (warm) | n/a | ~2.5 s (mostly the external ArcGIS 3D scene) |
| Each open projection page | recomputed all figures every 1.5 s | recomputes only when the selection changes |
| Data sent per page load (charts/map) | 217 KB uncompressed | **29 KB** (zstd/gzip, 7.5× smaller) |
| First visitor after a restart | waits for the opening view to be computed | opening view pre-built at startup |

The optimised code was checked against the previous version: all year snapshots, the 480k-row
yearly panel and all unit-statistics tables are identical, except for the intended fixes below.

**Remaining headroom.** About 70% of an uncached interaction is now Plotly Express building figures,
not pandas. Next steps, if needed:

1. Lazy-load the ArcGIS 3D iframe (the heaviest part of page load).
2. Build the hot figures with `plotly.graph_objects` instead of `px`, or precompute the 105 yearly
   island views at startup.
3. Ship the CSV as Parquet, which loads faster and is smaller (adds a `pyarrow` dependency).

## Behaviour changes the client should know about

1. **"Leaving" time series now shows data.** It was always empty because the filter was
   self-contradictory (`move_out > end_of_year` and then `< end_of_year`).
2. **The dashboard no longer freezes on some years.** Households earning more than $1.5M fell
   outside every age/income band, which crashed the sunburst, so nothing updated (e.g. from
   year 2079 on). The richest and poorest bands are now open-ended. 94 rows of the
   "Income Groups" time series that were silently dropped are now counted as "Upper".
3. The sunburst title said "in WIRE" for every scope; it now names the selected scope.
4. The fixed pixel sizes for the 2021 touch screen and projectors are gone; all pages fill the screen.

## Upgrade breakages that were fixed (useful for the next upgrade)

- Dash: `dash_core_components`/`dash_html_components` → `from dash import dcc, html`; `app.run_server` → `app.run`.
- Plotly 7: `hsv(...)` colour strings rejected → converted to hex at load; `choropleth_mapbox` → `choropleth_map`.
- GeoPandas 1.x: `gpd.options.use_pygeos` removed.
- pandas 3: chained `fillna(inplace=True)` no longer writes back.

## Known quirks, left as they were (model semantics, ask before changing)

- A household is a resident in year Y only if it was there for the *whole* year, so households
  that move in mid-year are not counted until the next year, and `stay_go == 'new'` is rare.
- Age is `year - birth year` (birthdays ignored).
- The per-building WIRE time series filters `year < selected` while the other series use `<=`.
- The projection-page state is global. On a public site, any visitor's selection changes what
  the projection pages show. This is fine for a kiosk; it would need per-session state otherwise.

## Republishing (M6) checklist

1. Review and merge `revive-2026` into `main` (or point Render at the branch).
2. In the Render service settings, check that:
   - the start command matches `render.yaml`: `gunicorn app:server --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`;
   - the Python version is 3.13 (`PYTHON_VERSION` env var or `.python-version`);
   - the build command is `pip install -r requirements.txt`.
3. After deploy, open `/`, move the slider, switch the scale to *Individual Building* and click
   a building, try each Time series and Detail chart option, and open `/ProjDash` in a second tab.

## Suggested next refactors (not urgent)

- Split `app.py` into `data.py`, `figures.py`, `layout.py` and `callbacks.py`.
- Rename legacy identifiers (e.g. `reasulToLeaveByTime`, `icnome_color_census`, `ageLbaelsSmall`).
- Add a CI job that runs `tests/smoke_test.py`.

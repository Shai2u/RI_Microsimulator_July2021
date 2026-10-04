# Roosevelt Island Microsimulator Dashboard

An interactive [Dash](https://dash.plotly.com/) dashboard for exploring the results of an
agent-based housing microsimulation of Roosevelt Island, NYC (1976–2080). Each simulated
household moves in, ages, changes income, and eventually leaves (because of rent burden,
mortgage burden, total burden, or death). The dashboard shows how the island's market
and affordable units, ages and incomes change over time, by building or by building group
(WIRE vs. Northtown & Southtown).

The app was built in 2021 and revived in October 2026 (see [HANDOFF.md](HANDOFF.md)).

## Quick start

Requires Python 3.13 (see `.python-version`).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py                         # http://127.0.0.1:8050
# or, as in production:
gunicorn app:server --workers 1 --threads 4 --bind 127.0.0.1:8050
```

Startup takes about 2 seconds; all data ships with the repository.

## Pages

| Path        | Purpose |
|-------------|---------|
| `/`         | Main dashboard (originally a touch screen): 3D scene, map, year slider, time series, sunburst and detail chart. Works on phone, tablet and desktop. |
| `/ProjDash` | Projection view: mirrors the charts currently selected on the main dashboard. |
| `/Proj3D`   | Projection view: mirrors the map and the 3D scene. |
| `/Only3D`   | Projection view: 3D scene only. |

The projection pages were made for an installation where a touch screen drives one or more
projectors. They poll every 1.5 s and re-render only when the selection changes (see *Shared state*).

### Using the main dashboard

- **Scale**: whole island, WIRE (aggregated or per building), Northtown & Southtown, or
  *Individual Building*. For the building view, choose it and then **click a building on the map**.
- **Year**: the snapshot year; time series run up to this year.
- **Map colour / Time series / Detail chart**: what the map, the top chart and the bottom-right
  chart show.
- **3D view**: "Follows Selection" moves the ArcGIS 3D scene camera to the selected building/group.

## Project layout

```
app.py                      the whole application (data prep, figures, layout, callbacks)
assets/legacy_resources/    data the app loads
  result_dec_21_955.csv       simulation output: one row per household tenancy
  rib_feb_11.geojson          building footprints with group / construction year
  *.xlsx                      colour palettes and age/income band definitions
Data/wiki/                  sample inputs and screenshots documenting the simulation (not loaded)
tests/smoke_test.py         runs every callback path without a browser
render.yaml                 Render deployment blueprint
state/                      runtime only (gitignored): shared selection for the projection pages
```

`om__boar.glb` is a legacy 3D asset that the app does not use.

### How `app.py` is organised (top to bottom)

1. **Data loading.** Reads the CSV (used columns only), the GeoJSON and the colour spreadsheets.
   `hsv()` colours are converted to hex because Plotly 7 rejects them.
2. **Domain helpers.** `bldFunctionality.getAffordableMarketPerYear3(year)` returns the
   households living in a building for the whole year, with age/income groups and colours.
   It is cached per year. `ageIncomeGroups`, `ageClass` and `incomeClass` are vectorised.
3. **`sim_plot`.** Figure builders (time series, sunburst, bubbles, treemaps, histograms).
   Figures carry no fixed size; they fill their container.
4. **Yearly panel.** `allByYear` stacks every year's residents (`stay`/`new`) and movers-out
   (`out`), about 480k rows. It is built once at startup and feeds the time series and the
   market/affordable statistics.
5. **Map.** `updateMapYear1` builds the MapLibre choropleth (`px.choropleth_map`; no token needed).
6. **Layout.** A Bootstrap grid (`dash-bootstrap-components`) with three columns on wide screens,
   two on tablets, and stacked on phones.
7. **Validation, shared state, callbacks.** `TimeSunBurstContextFigure` validates the selection,
   records it for the projection pages, and returns cached figures from `dashboardFigures`.

## Data model in one paragraph

Each CSV row is one household's tenancy in one apartment (`ap_index`) of a building, with
`move_in`/`move_out`, `birth_date`, `income`, `annual_expenses`, `affordable_living`
(1 = affordable/protected unit), `tenant_cycle` and the `cause` of leaving. A household
counts as a resident in year *Y* if it moved in by 1 Jan *Y* and left after 1 Jan *Y+1*. It
counts as having left in year *Y* if `move_out` falls in *Y*. Age/income groups come from
`group_color_jan_7.xlsx`: each band starts at its `min`, and the youngest/oldest and
poorest/richest bands are open-ended.

## Shared state (projection pages)

Each interaction writes the current selection to `state/dashboard.json` and `state/map.json`,
using atomic writes. The projection pages read those files. This works for a single instance;
if you ever run more than one instance, move the state to a shared store (e.g. Redis).

## Security notes

- Every value coming from the browser (dropdowns, slider, clicked building) is checked against
  an allow-list before use, and no user input is interpolated into `DataFrame.query()` or `eval`.
- The app runs with `debug=False`; responses carry `X-Content-Type-Options`, `X-Frame-Options`
  and `Referrer-Policy` headers.
- The app has no authentication: it only shows simulation results.

## Testing

```bash
python tests/smoke_test.py          # every menu combination + 4 years + hostile input (~2 min)
python tests/smoke_test.py --full   # every year 1976-2080 (~5 min)
```

Run it after any dependency upgrade. Plotly, Dash and pandas major versions have each broken
this app before (see HANDOFF.md).

## Deployment (Render)

`render.yaml` describes the service: `pip install -r requirements.txt`, then
`gunicorn app:server --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`.
Peak memory is about 350–420 MB, which fits the 512 MB instance. Keep **one** worker, because
each worker loads its own copy of the data. A push to the deployed branch redeploys if
auto-deploy is enabled on the Render service.

## Dependencies

Direct dependencies are pinned in `requirements.txt` (Dash 4, Plotly 7, pandas 3, GeoPandas 1.2).
To upgrade: bump the versions, reinstall, run the smoke test, and click through the pages.

## License

MIT, see [LICENSE](LICENSE).

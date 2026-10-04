# Publishing on Render.com

How to put the Roosevelt Island Microsimulator dashboard online with [Render](https://render.com).
You don't need access to the GitHub repository: it is public, so Render can deploy it from its URL.

## 1. Create the account

Sign up at **https://render.com** with an email, Google or GitHub login.
The free plan should not need a credit card (check https://render.com/pricing for the current terms).

## 2. Create the web service

1. In the Render dashboard click **New → Web Service**.
2. Choose **Public Git Repository** and paste:

   ```
   https://github.com/Shai2u/RI_Microsimulator_July2021
   ```

3. Fill in the settings:

   | Setting | Value |
   |---|---|
   | Name | `roosevelt-island-microsimulator` (or any free name; `ri-dashboard` is taken). The site address becomes `https://<name>.onrender.com` |
   | Branch | `revive-2026` (or `main` once the branch is merged) |
   | Region | Frankfurt if most viewers are in Israel or Europe, Ohio if they are in the US |
   | Runtime | Python 3 |
   | Build command | `pip install -r requirements.txt` |
   | Start command | `gunicorn app:server --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT` |
   | Instance type | Free |

4. Under **Environment Variables** add:

   | Key | Value |
   |---|---|
   | `PYTHON_VERSION` | `3.13.2` |

5. Click **Create Web Service**. The first build takes a few minutes. When the log shows
   `Listening at: http://0.0.0.0:...`, open the `.onrender.com` link at the top of the page.

Keep **one** worker (`--workers 1`). Each worker loads its own copy of the data, and two would
exceed the 512 MB of the small instances.

## 3. Check that it works

- `/`: the main dashboard loads with the map, time series, sunburst and detail chart.
- Move the **Year** slider; the charts and the map update.
- Set **Scale** to *Individual Building (click map)* and click a building on the map.
- Open `/ProjDash` in a second tab; it mirrors the selection from the main page.

## 4. Updating the site

A service deployed from a public URL does **not** redeploy automatically when code is pushed.
After new commits are pushed to the branch, open the service in Render and click
**Manual Deploy → Deploy latest commit**.

For automatic deploys on every push, connect the GitHub account that owns the repository
(Account settings → Git providers) and recreate the service from the connected repository.
The settings above stay the same, and `render.yaml` in the repository contains them.

## 5. Plans and costs

| | Free | Starter (paid) |
|---|---|---|
| Price | $0 | about $7/month (check current pricing) |
| Credit card | not required | required, and it must stay on the account |
| Behaviour | sleeps after ~15 minutes without visitors; the next visitor waits ~30–60 s while it wakes | always on, no wake-up delay |

To upgrade: open the service → **Settings → Instance Type → Starter**. Don't remove the card from
an account with a paid service, or the next invoice fails and the service is suspended.

## 6. Sharing access

The account owner can invite other people to the Render workspace (**Workspace settings → Members**),
so a developer can deploy and read logs while the owner keeps billing.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Build fails while installing packages | `PYTHON_VERSION` is missing or wrong; set it to `3.13.2` and redeploy. |
| "Out of memory" or the service restarts | More than one worker is running; check that the start command has `--workers 1`. |
| The site shows an old version | Click **Manual Deploy → Deploy latest commit**, and check the branch setting. |
| Charts load but the 3D panel is blank | The 3D scene is hosted by ArcGIS (technion-gis.maps.arcgis.com); check that it opens in a browser on its own. |
| First visit takes about a minute | That is the free plan waking up; upgrade to Starter to avoid it. |

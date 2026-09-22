# Philippines El Niño Watch

A free, province-level map of where El Niño drought conditions are
expected each month, plus PAGASA's national tropical cyclone outlook,
built from DOST-PAGASA and Manila Observatory's public outlooks. Meant
for MFIs, cooperatives, NGOs, and anyone else planning around clients or
operations spread across the Philippines, most MFIs serve exactly the
kind of agriculture- and weather-exposed clients this map is trying to
flag early.

**[Open the live map](output/ph_el_nino_watch.html)** — it's a
single self-contained HTML file, no server needed. Download it and open
it in any browser, or serve it from GitHub Pages.

This is **not an official PAGASA or Manila Observatory product**. It's a
third-party visualization of their public bulletins. Always confirm
against PAGASA's own advisories before acting on anything here — see
"Disclaimer" below.

## What it shows

- A province-by-province El Niño drought alert level (Watch, Prepare,
  Act, Respond) for each month from September 2026 to February 2027,
  driven by PAGASA's dry condition / dry spell / drought status and
  rainfall-deficit thresholds.
- PAGASA's national tropical cyclone frequency outlook, shown each month
  as a banner (not a per-province signal, since PAGASA doesn't forecast
  which specific province a cyclone will hit this far out).
- Search by province or region, a monthly rainfall-vs-normal table per
  province, and a "what to consider" section per alert level, adapted
  from Manila Observatory's own Watch · Learn · Prepare · Act framework.

## Methodology

The alert-level logic lives in `scripts/01_build_provincial_alerts.py`
and is fully described in the code comments there. In short: PAGASA's
published dry condition / dry spell / drought status per province,
escalated by rainfall thresholds (≤40% of normal → Prepare, 41-60% →
Watch) and a one-month-ahead warning.

An earlier version of this map also computed a second, independent
alert axis for Habagat (Southwest Monsoon) flood risk. It was dropped
from the public version because the underlying Habagat bulletin only
covered the first of the six months in this dataset, which made that
axis look stale for the rest of the window — see `ROADMAP.md` if you
want to pick it back up with a proper seasonal flood data source.

## Sources

| What | Source |
|---|---|
| Provincial rainfall %, dry status, cyclone outlook | DOST-PAGASA Climate Outlook (published monthly at [bagong.pagasa.dost.gov.ph/climate](https://bagong.pagasa.dost.gov.ph/climate)) |
| ENSO framing, Watch · Learn · Prepare · Act guidance | Manila Observatory Drought Watch bulletins |
| Province boundaries | PSA, faeldon (2023 simplified boundary set) |
| Basemap tiles | OpenStreetMap by default; optionally CARTO's Voyager style if you configure your own key -- see "Basemap tiles" below |

Full detail in `sources.json`. If you spot an attribution error, please
open an issue.

## Setup

```bash
python3 --version   # 3.9+, no extra packages needed
```

## Rebuilding the map

```bash
bash build.sh
```

Regenerates `output/ph_el_nino_watch.html` from whatever is
currently in `data/`.

## Basemap tiles

By default, the map uses free, keyless OpenStreetMap tiles -- nothing to
configure, works immediately after `bash build.sh`.

If you'd rather use CARTO's Voyager style (a bit more polished, subtler
labels), you can plug in your own free CARTO account:

1. Sign up at [carto.com](https://carto.com) (their Basemaps free tier
   covers this use case) and get an API key from your account's
   Basemaps section.
2. Copy the template: `cp config.local.example.json config.local.json`.
3. Put your key in `config.local.json`:
   ```json
   {"carto_api_key": "your-key-here"}
   ```
   This file is gitignored -- it will never be committed. You can also
   set a `CARTO_API_KEY` environment variable instead if you'd rather
   not have it in a file at all.
4. `bash build.sh` -- the console will confirm which basemap it used.

**Never commit a real key.** `config.local.json` is gitignored precisely
so this can't happen by accident; `config.local.example.json` (tracked)
is just the template, with no real key in it. If you ever do commit one
by mistake, rotate/regenerate it in your CARTO dashboard immediately --
removing it from a later commit does not remove it from git history.

## Deploying to GitHub Pages

GitHub Pages is static hosting with no backend: **whatever ends up in
the page it serves is 100% public**, including any tile URL and any key
in it, the same way any client-side map key is visible in your browser's
network tab. There is no way to keep a key secret in a pure static
deployment. Keeping it out of the *repository's source* (which this
project already does) and keeping it out of the *deployed page* are two
different things -- pick the option below based on which one you
actually need.

**Option A -- simplest, fully key-free (recommended for most people):**
commit the default `output/ph_el_nino_watch.html` (built without
a CARTO key, so it uses OpenStreetMap tiles) and point GitHub Pages at
it directly: Settings -> Pages -> Deploy from a branch -> pick `main`
and the folder containing it (rename/copy it to `index.html` at the repo
root, or serve from `/output` and link to the file directly). Nothing
sensitive is ever involved.

**Option B -- CARTO's look on the live site, key kept out of the repo
(but not out of the deployed page):** this repo includes
`.github/workflows/deploy.yml`, a GitHub Actions workflow that rebuilds
the map on every push to `main` and publishes it via GitHub Pages.
1. In your repo: Settings -> Secrets and variables -> Actions -> New
   repository secret, name it `CARTO_API_KEY`, paste your key.
2. Settings -> Pages -> Source -> GitHub Actions.
3. Push to `main`. The workflow builds with your key (injected only at
   build time, never written into any committed file) and deploys the
   result.
4. Understand that once deployed, **your key is visible in the live
   page's source and network requests** to anyone who looks -- that's
   inherent to how client-side map tiles work, not a flaw in this setup.
   If your CARTO account supports restricting a key to specific
   domains/referrers, restrict this one to your `*.github.io` domain so
   it can't usefully be copied and reused elsewhere even though the
   value itself is visible.

If you don't set the `CARTO_API_KEY` secret, the same workflow just
deploys the free OpenStreetMap version -- Option B degrades to Option A
automatically.

## Updating for a new PAGASA outlook

1. Get the new PAGASA "Forecast Rainfall Matrix," "Outlook over
   Different Provinces," and "Forecast Tropical Cyclone Frequency"
   tables (PAGASA publishes these monthly).
2. Open `data/provincial_risk_source.py` — follow the docstring at the
   top exactly.
3. `bash build.sh`.
4. Open the rebuilt map and click through the new months before
   publishing.

## Agricultural exposure layer

Each province's detail card also shows an "Agricultural exposure" line:
rice (palay) and corn volume of production (metric tons) and area
harvested (hectares), for the most recent complete year available. This
is purely informational context -- e.g. "this drought-flagged province
also has a lot of rice/corn production at stake" -- and is entirely
separate from, and never changes, the PAGASA-derived drought alert level,
color, or any of `lvl()`/`style()`'s logic in `map/map_template.html`.

The data comes from the [Philippine Statistics Authority (PSA)
OpenSTAT](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/CS) PXWeb API
(see `sources.json`), cached in `data/processed/agriculture_exposure.json`.
Some provinces show a fallback note instead of numbers:
- Metro Manila/NCR has no PSA crop-production row at all.
- A handful of PSA province rows needed reconciliation against this
  project's 82 province keys (Maguindanao del Norte/Sur summed into
  `MAGUINDANAO`, Highly Urbanized Cities folded into their surrounding
  province, etc.) -- see the docstring of
  `scripts/00_fetch_agriculture_exposure.py` for the full, documented
  list of rules and why they're resolved that way.

**To refresh it:**

```
python3 scripts/00_fetch_agriculture_exposure.py
bash build.sh
```

Unlike `data/provincial_risk_source.py` (updated by hand from a new
PAGASA PDF), this layer is fetched live from PSA's API, so re-running the
script alone pulls the latest published figures -- no manual
transcription needed. This script needs network access and is
deliberately **not** part of `build.sh`, which stays fully offline; if
you never run it, the map just shows the "no data" fallback for every
province.

## Poverty incidence (vulnerability proxy)

Each province's detail card also shows a "Poverty incidence" line: the
share of the population below the poverty line, for the most recent
year PSA has published (2023 at time of writing). This is a general
vulnerability/adaptive-capacity proxy -- provinces with higher poverty
incidence generally have less capacity to cope with and recover from a
drought -- not an El Niño-specific index. The original plan (see
`ROADMAP.md` "Methodology gaps vs. comparable ENSO/drought tools") was
to overlay the UPLB study "Relative Vulnerability of the Different
Provinces of the Philippines to El Niño-Induced Droughts" (David et al.
2007), which ranks provinces by historical El Niño rainfall-departure
data. That paper's actual data table turned out to be inaccessible
anywhere legitimate (its UKDR repository entry says "Digital Copy:
none"; ResearchGate says no full text is available), so this poverty
statistic shipped instead, as a more general but fully open and
regularly-updated substitute. No "HIGH/MODERATE/LOW" tier is derived
from the percentage -- that would be an unreviewed editorial judgment
call, so only the raw PSA number is shown. Like the agriculture exposure
layer, this is purely informational context and is entirely separate
from, and never changes, the PAGASA-derived drought alert level, color,
or any of `lvl()`/`style()`'s logic in `map/map_template.html` -- and it
is never blended with the agriculture exposure numbers.

The data comes from [PSA
OpenSTAT](https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1F/FY)'s PXWeb
API (see `sources.json`), cached in `data/processed/vulnerability.json`.
A couple of Highly-Urbanized-City rows (Isabela City, Cotabato City) have
no natural home among this project's 82 province keys and are omitted
rather than folded into a neighboring province -- poverty incidence is a
rate, so (unlike the agriculture layer's crop-tonnage totals) it cannot
be meaningfully summed or averaged without population weights. See the
docstring of `scripts/00_fetch_vulnerability_data.py` for the full,
documented reconciliation rules, including how Metro Manila and
Maguindanao (which PSA itself reports as a combined figure alongside its
del Norte/del Sur split) are handled.

**To refresh it:**

```
python3 scripts/00_fetch_vulnerability_data.py
bash build.sh
```

This script needs network access and is deliberately **not** part of
`build.sh`. PSA's poverty statistics come from its triennial income
survey (2018, 2021, 2023 so far), so there's little reason to re-run
this more than once every few years -- unlike the agriculture layer,
which is worth refreshing quarterly.

## Adapting this for your own institution

This project intentionally carries no organization-specific data. If
you want to overlay your own branch/office locations:

- The cleanest approach is a client-side upload feature (see
  `ROADMAP.md`) so your location data never has to leave your browser
  or be committed to a public repo.
- If you fork this to add your own data, **do not commit it to a public
  repository** — even aggregated counts can reveal a competitor's
  operational footprint. Keep organization-specific data in a private
  fork or a `.gitignore`'d local file.

## Disclaimer

This map is provided for general planning and awareness purposes only.
It is not an official PAGASA or Manila Observatory product, is not
real-time, and should never be the sole basis for an operational,
financial, or safety decision. Always check PAGASA's own advisories
(pagasa.dost.gov.ph) for the current official outlook.

## License

MIT — see `LICENSE`. The code and map template are MIT-licensed; the
underlying PAGASA/Manila Observatory climate data and PSA/faeldon
boundary data are used under their own public-outlook terms, not
relicensed by this project.

# Roadmap / candidate future layers

This v1 is deliberately scoped to one thing done well: a province-level
El Nino drought alert map from PAGASA and Manila Observatory's public
outlooks, with PAGASA's tropical cyclone frequency outlook noted monthly
as context. The ideas below were raised while building it and are worth
pursuing, but need their own research/integration pass before shipping.
Recorded here so they aren't lost.

## Habagat/flood axis (removed from v1)

v1 originally computed a second, independent alert axis for Habagat
(Southwest Monsoon) flood risk, including a "flood on dry ground" rule
reviewed with Manila Observatory. It was removed because the underlying
Habagat bulletin only covered the first month of this dataset's window,
which made the axis look stale for the other five months. If this comes
back, it should be re-scoped as a proper seasonal-forecast layer (e.g.
tied to Google FloodHub below) rather than a single bulletin's snapshot.

## Upload-your-own-locations matcher

The original motivation for a "no proprietary data" public version: let
any MFI, cooperative, or NGO upload a CSV of their own branch/office
locations (city or province name is enough) and see which of their own
locations fall into a flagged province each month, entirely client-side
so their location list never leaves their browser. Needs a province/city
name-matching step tolerant of how different institutions format their
own location lists.

## Google FloodHub (river flood forecasts)

Verified (2026-09-21): [sites.research.google/gr/floodforecasting](https://sites.research.google/gr/floodforecasting)
covers 150+ countries, riverine flood forecasts up to 7 days out and
urban flash-flood forecasts up to 24 hours out, free and public, updated
daily. There's a published hydrology model, an API (gated, request
access), the Caravan streamflow dataset, and an open-source model repo.
This lines up directly with PAGASA's own river-basin warnings (Pampanga,
Agno, Abra, Cagayan, Bicol) that already drive part of this project's
flood-on-dry-ground rule. Not yet confirmed: exact river-basin-level
coverage for the Philippines specifically (floodhub.google.com itself
wasn't reachable to check at research time) -- verify that before
committing to integration.

## Philippine agriculture exposure

**Implemented (2026-09-22).** See README.md "Agricultural exposure
layer" for what it shows and how to refresh it, and
`scripts/00_fetch_agriculture_exposure.py`'s docstring for the full
reconciliation rules. Summary of what shipped, for anyone revisiting
this:

- Built on PSA OpenSTAT's PXWeb API (`DB/2E/CS`), specifically the
  "Palay and Corn: Volume of Production" and "...: Area Harvested"
  tables, discovered by title match (not a hardcoded table ID) since
  PXWeb table IDs can shift. Uses the most recent year with a complete
  "Annual" figure (2025 at implementation time), fetched via the
  PX-generic `json` response format -- this server's `json-stat2` format
  was found to return malformed/truncated data, so don't use it here.
- All of the province-name reconciliation risks called out below were
  real and handled: Maguindanao del Norte/Sur summed into `MAGUINDANAO`;
  Metro Manila/NCR set to an explicit null + note (PSA has no NCR
  crop-production row at all); the five Highly Urbanized Cities folded
  into their mother province; and Negros Occidental/Oriental, Siquijor,
  and Sulu's duplicate-region rows resolved by picking whichever
  duplicate actually has a non-missing figure (rather than a hardcoded
  "always prefer region X" rule) -- PSA had in fact already stopped
  populating the legacy-region rows for these by the time this was
  built, the opposite of what the original scoping notes below assumed,
  which is exactly why the resolution rule is data-driven, not static.
- Fisheries data, PSA's other regions/provinces beyond rice and corn,
  and the one-time 2022 Census of Agriculture and Fisheries backdrop
  layer mentioned in the original scoping notes below were not pursued
  -- still open if this layer proves useful and someone wants to extend
  it.
- **Redesigned (2026-09-22)** three times in the same session, in order:
  1. From a plain-text "X MT produced" line (no reference point for a
     reader -- is that a lot?) to a rank/share presentation per crop:
     rank ("#1 of 82 provinces") as plain text, plus a linear meter bar.
  2. That bar's width scaled to the top-producing province instead of
     to 100%, so a "full" bar didn't actually mean 100% of national
     output -- visually contradicting the percentage printed right next
     to it. Fixed once reported: bar width changed to equal the stated
     share exactly (0-100%).
  3. Even accurate, a linear bar still looked unsatisfying: production
     is spread across many provinces, so nearly every bar was a short,
     near-empty sliver that read as broken or unfinished rather than
     intentional. Replaced the bar with a small ring per crop (SVG,
     stroke-dasharray arc) -- same honest 0-100%-of-national-production
     encoding as the fixed bar, but a short arc on a ring still reads
     as a deliberate percentage indicator at any fill level, the way a
     loading spinner or progress ring does, instead of looking like an
     incomplete bar. Rank stays plain text either way; ordinal position
     was never something the shape needed to imply.
  Deliberately does not attempt to estimate a drought-impact percentage
  on production at any point in this -- that needs real agronomic
  yield-loss modeling this project has no basis for.

Original scoping notes (kept for context): PSA OpenSTAT
(`DB/2E/CS` for crops, `DB/2E/FS` for fisheries) — confirmed live, queryable
as JSON-stat/CSV (not PDF), quarterly-updated (latest table stamps
Jul-Sep 2026), and covers rice, corn, coconut, sugarcane, and fisheries
volume + peso value at province granularity. Openly licensed with source
attribution, same pattern as the PAGASA/Manila Observatory citations
already in `sources.json`. DA has no separate open dataset of its own
(the old Bureau of Agricultural Statistics was absorbed into PSA in
2013); FAOSTAT and World Bank only publish PH data at the national
level, not per-province; DOST's agriculture-relevant public data is all
hazard-side (SPEI drought maps, Project NOAH flood/landslide layers),
not exposure. PhilRice's PRiSM/CS Map is the closest existing PH system
combining rice-area exposure with hazard, but its data is request-gated,
not an open API -- worth citing as methodology, not usable as a v1 data
source.

**The real scoping risk is province-name reconciliation, not data
availability.** PSA's current tables don't line up 1:1 with this
project's 82-key province list:
- `Maguindanao del Norte` / `Maguindanao del Sur` are reported
  separately (2022 PSGC split); the project's single `MAGUINDANAO` key
  needs a merge step.
- NCR/Metro Manila has no crop-production row at all -- needs an
  explicit N/A convention, not a lookup-miss.
- Highly Urbanized Cities (Puerto Princesa, Bacolod, Zamboanga City,
  Davao City, Butuan) are reported as their own rows, separate from
  their "mother" province -- needs a fold-in-or-drop policy.
- Negros Occidental, Negros Oriental, and Siquijor each appear twice
  (once under their old region, once under "Negros Island Region") --
  a naive pull double-counts these three.
Build a small, tested province-name reconciliation table (cross-checked
against PSA's own published PSGC) before wiring any PSA table into the
pipeline. Secondary option once the recurring production numbers are
working: PSA's 2022 Census of Agriculture and Fisheries for a
one-time farm-count/farm-area backdrop layer (census, not a series --
don't try to refresh it monthly).

## Methodology gaps vs. comparable ENSO/drought tools

Researched (2026-09-22), comparing this project's approach (PAGASA's
monthly Climate Outlook bulletin, manually transcribed, turned into a
categorical Watch/Prepare/Act/Respond level per province) against IRI,
NOAA CPC, Copernicus C3S, FEWS NET, and existing Philippines-specific
studies. Two findings stood out as worth acting on, both cheap:

- **Every comparable tool publishes a probability, never a bare
  category.** PAGASA's own bulletin already states this (e.g. "70%
  chance of below-normal rainfall") but the current pipeline discards
  it in favor of just the rainfall-%-of-normal midpoint. Capturing that
  number during the same manual transcription and showing it alongside
  the alert level costs nothing new to gather and brings the map in
  line with standard practice (see IRI:
  https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/,
  NOAA CPC: https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/outlook/).
- **This project has a hazard signal but no exposure/vulnerability
  signal**, unlike IPCC AR5-style risk frameworks (Risk = Hazard ×
  Exposure × Vulnerability) used by INFORM
  (https://drmkc.jrc.ec.europa.eu/inform-index/INFORM-Risk/Methodology)
  and FEWS NET. The original candidate here was a ready-made, static,
  Philippines-specific, El Nino-specific index: the UPLB study "Relative
  Vulnerability of the Different Provinces of the Philippines to El
  Nino-Induced Droughts" (David et al. 2007,
  https://www.ukdr.uplb.edu.ph/journal-articles/2741/), which ranks all
  provinces from historical El Nino rainfall-departure data.
  **Tried, then removed (2026-09-22).** On investigation the UPLB
  study's actual data table turned out to be inaccessible anywhere
  legitimate (UKDR's own repository entry says "Digital Copy: none";
  ResearchGate says "No full-text available, request from authors"),
  so this shipped instead as PSA OpenSTAT poverty incidence -- a more
  general (not El Nino-specific) vulnerability/adaptive-capacity proxy,
  shown as a plain percentage alongside the drought card, never blended
  into the alert level. It was pulled from the map shortly after to
  simplify the province card and put design effort into the
  agriculture exposure layer instead (see that section above) rather
  than running two separate socioeconomic-context layers at once. The
  fetch script and cached data (`scripts/00_fetch_vulnerability_data.py`,
  `data/processed/vulnerability.json`) were deleted along with it rather
  than left as dead code; the PSA table (`DB/1F/FY`, "Poverty Incidence
  Among Population... by Region and Province") is still live if this
  gets revisited, and the reconciliation notes are worth re-reading
  first: poverty incidence is a rate, so Highly Urbanized City rows
  can't be summed/averaged into a province the way the agriculture
  layer's crop tonnage can, and Maguindanao has its own PSA-reported
  combined figure rather than needing a home-grown average of its del
  Norte/del Sur split. If an El Nino-specific vulnerability index ever
  becomes accessible, that -- not a generic poverty proxy -- is the
  better candidate for actually combining with the hazard axis, using a
  geometric mean (or a simple "vulnerability tier nudges the level by
  +/-1" rule) rather than an averaged score -- INFORM and the Marinduque
  barangay-level risk study
  (https://link.springer.com/article/10.1007/s11069-022-05795-w) both
  found that averaging lets a strong hazard signal get diluted by low
  vulnerability, which is the wrong direction for an early-warning tool.

Lower priority: PAGASA also publishes a weekly, 4-week-lead
Sub-Seasonal-to-Seasonal rainfall-exceedance forecast
(https://bagong.pagasa.dost.gov.ph/climate/climate-prediction/sub-seasonal2),
faster-cadence than the monthly bulletin this project uses. Worth an
occasional manual cross-check for provinces already at Act/Respond
(catches a fast-onset dry spell ~3 weeks sooner) but not worth building
a second automated pipeline around.

On cadence: this project's monthly-update, ~6-month rolling window is
in line with CPC/IRI/C3S/PAGASA's own practice -- not a gap.

## Community ground-truth reports

**Implemented (2026-09-22), low-cost tier, including photo upload.**
Click "Report what you're seeing" on any province's detail card to
open the "feels like"-style form described below; it writes to a
Firebase (Firestore + Storage) project. See README.md "Community
reports" for how to review submissions and why the Firebase web config
is safe to commit. Firestore security rules (set in the Firebase
Console, not in this repo) allow anyone to create a report with the
required fields and block all reads/edits/deletes except via the
Console -- verified directly: a valid submission succeeds, a malformed
one is rejected server-side, and an attempted read is rejected
server-side too, so the "private moderator inbox" framing below is
actually enforced, not just a client-side convention.

**Public Reports tab, added (2026-09-23), in two steps.** User first
asked for submitted reports to be publicly visible, not just
moderator-only -- a real change from the original framing above.

Step 1: rather than build the unmoderated version (any report visible
to every visitor the moment it's submitted, which is exactly the
misinformation vector this project's design was originally built to
avoid), added a moderation gate -- Firestore rules allowed `get`/`list`
only for documents where `status == "approved"`, a field the `create`
rule explicitly forbade the client from setting itself, so a report
only became public once a moderator had individually approved it via
the Console.

Step 2, same day: user reconsidered, given this is explicitly a
proof-of-concept ("since this is a POC") for "an anonymous
community-based monitoring tool" -- reverted to auto-display for all
reports, with moderation happening *after* publishing instead of
before (a moderator "regularly reviewing the reports... to verify and
forward... to contacts/authorities from the reported locations", not
gatekeeping what the public sees). Firestore rules now allow `get`/
`list` unconditionally; the `create` rule still forbids the client
from setting `status`, kept in reserve for possible future moderator-
side tracking even though nothing currently reads it. Also added
optional `barangay`/`municipality` fields to the report form
specifically so a moderator knows who to forward a credible report to.

What stayed constant across both steps: the tab HTML-escapes every
field before rendering (verified against a synthetic report with
`<script>`/`<img onerror>` payloads at every step so far), and
`contact` is never rendered publicly regardless of the read-access
model. If a future maintainer wants to revisit gating the public tab
again (e.g. if the anonymous/unmoderated version turns out to attract
bad-faith submissions at scale), the `status` field and its
`create`-time restriction are already there to build on.

Step 3 (2026-09-23, same day): user asked to also display photos
publicly, discussed the billing-spike risk this raises first (see
below), decided to skip App Check for this POC pass and rely on
budget alerts instead, and asked for a success acknowledgment +
auto-close on the report form. `photoPath` is no longer excluded from
the public tab; Storage rules now allow public `read` (previously
`false`). Photos render via a client-constructed Storage download URL
(`storagePublicUrl()`) rather than an SDK `getDownloadURL()` call per
photo, so rendering N report cards doesn't cost N extra async
round-trips. On successful submission, the form shows a clear
acknowledgment and the modal auto-closes after ~1.8s (`setTimeout`),
and `reportsLoaded` is reset so the Reports tab refetches instead of
serving a stale cached list that wouldn't include the just-submitted
report.

**App Check was scoped, then explicitly skipped for this POC.**
Firebase App Check (reCAPTCHA v3, free tier -- verified against
Google's current pricing page, since they've since split the old
"classic v3" into a 3-tier "Essentials / Premium / Enterprise"
structure; Essentials is still free up to 10,000 assessments/month
and is what App Check's "reCAPTCHA v3" provider uses) is the standard
mitigation against exactly the risk this project now carries: public
create/read on Firestore and Storage with no rate limiting and no
verification that requests originate from the deployed site rather
than a script. User chose to skip it for now given the POC framing,
accepting that Google Cloud budget alerts are a strictly weaker,
notification-only backstop (they don't prevent overspend, only flag
it after it's started) rather than the access-control layer App Check
would provide. Revisit this if usage or abuse patterns suggest it's
warranted -- registering the app for App Check without yet flipping on
enforcement is low-risk and could be done as a monitoring-only trial
before committing either way.

**Photo capacity under the free tier**, worked out from Firebase's
verified pricing (see the agriculture/vulnerability-style research
elsewhere in this file for the pattern of citing verified numbers
rather than guessing): the 5MB-per-photo cap this project's Storage
rules enforce means the 5GB-month storage allowance bounds roughly
1,000 photos in the worst case (every photo at the cap) up to
~2,000-5,000 if photos average a more realistic 1-2MB. Upload
operations (5,000/month free) are unlikely to bind first at POC scale.
The tighter real-world constraint is usually the 100GB/month
**viewing** bandwidth, not storage or upload count -- every visitor who
opens the Reports tab downloads every photo shown there, with no
caching layer (this is a static site with no backend to add one
cheaply), so total free "budget" scales with (average photo size) x
(photos shown) x (how often people actually view the tab), not just
how many photos exist.

**Photo upload.** Initially scoped out (2026-09-22 morning) because
Firebase changed its policy in late 2024: Cloud Storage requires the
paid Blaze plan even for usage entirely within the free quota, and
requiring a credit card on file felt like too much to ask just to try
this feature. Revisited the same day once the user decided to enable
Blaze themselves. Two things worth recording for anyone else doing
this:
- Blaze's no-cost Storage quota (5GB stored, 100GB/month downloaded,
  5K/month uploads, 50K/month download operations, confirmed on
  Firebase's live pricing page) only applies in specific regions --
  us-central1, us-west1, us-east1 at the time this was set up. This
  project's Storage bucket uses one of those regions rather than
  something closer to the Philippines, since upload latency for an
  occasional report photo is a non-issue, but losing the free tier
  entirely by picking an ineligible region would not have been. Bucket
  region can't be changed after creation.
- Photo uploads are verified server-side by the same rigor as the text
  fields: a valid image under 5MB succeeds, an oversized file is
  rejected, and a non-image content type is rejected -- all confirmed
  directly against the live project, not assumed from the rules text.
  A report's `photoPath` field stores the Storage path only, never a
  download URL, since Storage read is blocked the same way Firestore
  read is -- viewing a photo means opening that path in the Console's
  Storage browser.

Original scoping notes below, kept for context on the free/full tiers
that weren't chosen and the reasoning behind the framing decision.

PAGASA already publishes its own
official "PH Meteorological Drought Monitor" (observed + forecast maps,
same Sep 2026-Feb 2027 window this project uses) at
https://www.pagasa.dost.gov.ph/climate/el-nino-la-nina/advisories, so
this project's forecast layer partly overlaps with an official source.
What PAGASA's tool does *not* have is any citizen input: a way for
people to report what they're actually seeing on the ground (water
shortage, crop stress, other drought symptoms) and have that reach a
moderator who can pass notable patterns on to PAGASA or a local DRRMO.
That's a genuinely different, complementary product, not a duplicate.

**Important framing decision, already settled:** this is NOT a public
"PAGASA said X, but actually Y" claims layer -- that would carry real
misinformation risk for a solo, unmoderated project, especially during
an actual emergency. Instead it's a **private report inbox with a
moderator in the loop**: residents submit what they're experiencing,
a moderator reviews and can escalate credible patterns to local
authorities or PAGASA, and nothing is published back to the public map
as a "fact" unless a moderator has actively chosen to surface it (e.g.
as an aggregate count, not a raw unverified claim).

**Interaction model:** click a province on the map (reusing the
existing province-selection UI) to open a short structured report, in
the spirit of a temperature "feels like" index but for El Nino
conditions -- a few simple rated dimensions (e.g. water availability,
crop/agricultural condition, general dryness) plus an optional
free-text field for their own words, rather than one open text box.

Three ways to build this, ordered by cost/effort:

| | Free | Low-cost | Full |
|---|---|---|---|
| Ingestion | GitHub Issue Form, deep-linked from a "Report what you're seeing" button (province + fields pre-filled into a new issue) | Real submission form on the map itself, posting to a small serverless backend (Supabase or Firebase free tier) | Same, plus lightweight anti-abuse (CAPTCHA or phone/email verification) and optional photo evidence |
| Moderation | GitHub's own issue UI -- label, comment, close (built-in, zero extra tooling) | A small password-gated admin view, or the backend's own built-in table browser | A purpose-built admin dashboard: review queues, verification status, audit trail |
| Escalation to PAGASA/LGU | Manual: `gh issue list --label needs-followup`, forward by hand | Same manual forward, but from a filtered backend query/export | Automated periodic digest, or API access if a partnership ever formed |
| Public surfacing | None automatic; any summary shown on the map would be hand-updated, same pattern as the monthly PAGASA transcription | Live per-province report counts pulled at page load (counts only, no raw unverified text, unless a moderator marks one "approved") | A moderated public "community observations" layer with history/trends, only for moderator-approved reports |
| Cost | $0 | $0 at low volume, realistically $0-10/mo | Roughly $20-100+/mo (managed DB, storage, verification service, likely hosting beyond GitHub Pages) |
| Effort | Small -- one issue template, one button | Medium -- first real backend this project would have | Large -- a genuine small web app, not a static site anymore |
| Main limitation | Requires a GitHub account to submit; "click your area" is really a pre-filled dropdown, not an actual map click; no live public counts | Real backend to operate and pay for, even if cheap | Meaningful ongoing cost and maintenance burden for a personal project |

**Recommendation if this gets built:** Free tier is the fastest way to
find out whether people actually want to submit reports at all, before
committing to backend work -- but it can't deliver the "click your
actual area on the map" interaction the low-cost and full tiers can.
Low-cost (Supabase/Firebase free tier) is the more likely real target:
it's the first tier that supports both the moderator-inbox model and
genuine map-click interactivity, without meaningful ongoing cost at
this project's likely scale.

## Solar irradiance / vegetation-stress (NDVI) data

Raised but needs scoping -- two different things could be meant here:
- **Solar/PV irradiance** (e.g. NASA POWER's free API) for backup-power
  planning during hydropower cutbacks, which correlate with drought.
- **Satellite vegetation-stress index (NDVI)**, which is more directly a
  drought-severity signal than a power-planning one.
Pick one (or both, separately) before building either.

## Not pursued for this project

- **Google WeatherNext / Weather Lab**: aimed at government agencies for
  precipitation/cyclone forecasting; PAGASA is already the province-level
  authority this project defers to, so this would mostly duplicate
  rather than add a layer.
- **Waze for Cities / Public Alerts**: real-time traffic and official
  alert broadcasting, not a climate-risk data source.

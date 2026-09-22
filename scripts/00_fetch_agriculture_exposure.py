#!/usr/bin/env python3
"""
scripts/00_fetch_agriculture_exposure.py

Pulls province-level rice (palay) and corn production and area-harvested
figures from the Philippine Statistics Authority (PSA) OpenSTAT PXWeb API
and writes data/processed/agriculture_exposure.json, keyed by the same
82 uppercase province keys used everywhere else in this project (see
data/processed/ph_provinces.json "key" and data/provincial_risk_source.py's
"PROVINCE NAME RULES").

This is an ADDITIVE, purely informational "exposure" layer -- e.g. "this
drought-flagged province also has a lot of rice/corn production at stake".
It never feeds into, and must never be wired into, the drought alert-level
logic in scripts/01_build_provincial_alerts.py or map/map_template.html's
lvl()/style() functions.

WHY THIS SCRIPT IS SEPARATE FROM build.sh
------------------------------------------
build.sh is deliberately offline/deterministic (see its comments and
README.md). This script needs network access to PSA's live API, so it is
NOT part of build.sh. Like data/provincial_risk_source.py (hand-updated
from a new PAGASA bulletin), this script is a periodic, manual maintainer
task:

    python3 scripts/00_fetch_agriculture_exposure.py
    bash build.sh

Re-run it every so often (PSA's crop tables update quarterly) to refresh
the cached data/processed/agriculture_exposure.json. If this script can't
run (no network, PSA API down) build.sh still works fine against whatever
agriculture_exposure.json is already checked in -- scripts/02_assemble_map.py
treats that file as optional.

WHAT IT FETCHES
----------------
PSA OpenSTAT's PXWeb API (https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/CS)
publishes, among others, two tables (discovered by title match below, since
PXWeb table IDs can shift -- do not hardcode them elsewhere):
  - "Palay and Corn: Volume of Production in Metric Tons by
     Ecosystem/Croptype, Quarter, Semester, Region and Province"
  - "Palay and Corn: Area Harvested in Hectares by Ecosystem/Croptype,
     Quarter, Semester, Region and Province"
Both are broken down by a "Geolocation" dimension (PHILIPPINES -> region
subtotal -> province, one PXWeb category per row) and a "Period" dimension
that includes a per-year "Annual" total. This script requests the
"Palay" and "Corn" (i.e. total, not the Irrigated/Rainfed or White/Yellow
sub-splits) Ecosystem/Croptype categories, for every Geolocation row, for
the most recent year whose "Annual" figure is populated for both crops at
the national (PHILIPPINES) level.

PROVINCE-NAME RECONCILIATION (see also ROADMAP.md "Philippine agriculture
exposure" and README.md)
--------------------------------------------------------------------------
PSA's ~108 Geolocation rows do not line up 1:1 with this project's 82
province keys. This script resolves the differences as follows, all
verified against the live API response (not just the metadata) as of the
date this script was last run -- see retrieved_at/period in the output:

1. Metro Manila / NCR: PSA's Geolocation list has NO National Capital
   Region entry at all in these two tables (no rice/corn production is
   tabulated for NCR). METRO MANILA is written with null figures and an
   explicit note, never a silent zero or a lookup crash.

2. Maguindanao del Norte / Maguindanao del Sur (the 2022 PSGC split) are
   reported as two separate BARMM rows. They are SUMMED into this
   project's single MAGUINDANAO key.

3. Highly Urbanized Cities are reported as their own Geolocation rows,
   separate from their surrounding ("mother") province. Each is SUMMED
   into its mother province, verified against the region block each HUC
   is actually listed under in the live API response:
     Puerto Princesa City -> PALAWAN     (listed under MIMAROPA, with Palawan)
     Bacolod City         -> NEGROS OCCIDENTAL (listed under Negros Island Region)
     Zamboanga City        -> ZAMBOANGA DEL SUR (listed under Region IX, with the Zamboanga provinces)
     City of Davao          -> DAVAO DEL SUR (listed under Region XI, with the Davao provinces)
     Butuan City            -> AGUSAN DEL NORTE (listed under Region XIII/Caraga, with Agusan del Norte)
   If a HUC's own figure is missing ("..") for the chosen period, it
   contributes 0 to the sum (documented per-province in "components"),
   since a missing separate breakout is far more likely than a genuine
   zero-production HUC, and the mother province's own figure already
   captures the surrounding area regardless.

4. Negros Occidental, Negros Oriental, Siquijor, and Sulu each appear
   TWICE in the Geolocation list under two different region groupings
   (Negros Occidental/Oriental/Siquijor under both their pre-2024 region
   -- Western/Central Visayas -- and "Negros Island Region"; Sulu under
   both a legacy Region IX/Zamboanga Peninsula row and its current BARMM
   row). Rather than hardcoding "always prefer region X", which would
   break the moment PSA's reporting convention shifts again (as it
   evidently already has: at the time this script was last run, PSA had
   in fact STOPPED populating the pre-2024-region rows for these three
   provinces and Sulu's legacy Region IX row, and was only reporting
   figures under Negros Island Region / BARMM -- the opposite of what an
   earlier draft of this script assumed), this script picks whichever of
   the two duplicate rows actually HAS a non-missing figure for the
   chosen crop/period. If both duplicate rows have real, non-missing
   figures at the same time (a genuine ambiguity), it does NOT guess or
   sum them -- it records the conflict in the output's
   "ambiguous_duplicate_rows" field so a maintainer can look at it, and
   falls back to the first-listed row's value so the pipeline still
   produces output.

5. Every PSA row that doesn't confidently match one of the above rules or
   a direct uppercase name match against ph_provinces.json's 82 keys is
   recorded in the output's "unmatched_psa_rows" field instead of being
   silently dropped. As of this script's last run that list was empty.

Usage:
    python3 scripts/00_fetch_agriculture_exposure.py
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_BASE = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/CS"
TABLE_LIST_URL = API_BASE
VOLUME_TITLE_MATCH = "palay and corn: volume of production"
AREA_TITLE_MATCH = "palay and corn: area harvested"
REQUEST_TIMEOUT = 30
# PSA's server 403s requests with Python's default urllib User-Agent string
# (and likely no User-Agent at all). A generic browser-like one is enough.
REQUEST_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; ph-el-nino-watch/1.0; +https://github.com/quielq/quielq-enso-watch)",
}

HUC_TO_MOTHER = {
    "PUERTO PRINCESA CITY": "PALAWAN",
    "BACOLOD CITY": "NEGROS OCCIDENTAL",
    "ZAMBOANGA CITY": "ZAMBOANGA DEL SUR",
    "CITY OF DAVAO": "DAVAO DEL SUR",
    "BUTUAN CITY": "AGUSAN DEL NORTE",
}
MAGUINDANAO_SPLIT = {"MAGUINDANAO DEL NORTE", "MAGUINDANAO DEL SUR"}
NO_PSA_DATA_NOTE = "No PSA crop-production data for this area (PSA's tables have no NCR/Metro Manila row)."


def _get_json(url, encoding="utf-8"):
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        raw = resp.read()
    return json.loads(raw.decode(encoding))


def _post_json(url, body, encoding="utf-8-sig"):
    """PXWeb's json-stat2 response was found to be broken on this server
    (it returns only a single cell regardless of query shape). The plain
    "json" (PX-generic) format works correctly and is used here instead;
    it comes back with a UTF-8 BOM, hence utf-8-sig."""
    headers = dict(REQUEST_HEADERS)
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        raw = resp.read()
    return json.loads(raw.decode(encoding))


def find_table_id(title_substr):
    listing = _get_json(TABLE_LIST_URL)
    matches = [t for t in listing if title_substr in t["text"].lower()]
    if not matches:
        raise SystemExit(
            f"ERROR: no PSA OpenSTAT table under {TABLE_LIST_URL} has a title "
            f"containing {title_substr!r}. PSA may have renamed/moved this table -- "
            f"inspect {TABLE_LIST_URL} by hand and update VOLUME_TITLE_MATCH/"
            f"AREA_TITLE_MATCH in this script."
        )
    if len(matches) > 1:
        print(f"WARNING: {len(matches)} tables matched {title_substr!r}, using the first: "
              f"{matches[0]['id']}", file=sys.stderr)
    return matches[0]["id"], matches[0]["text"]


def get_metadata(table_id):
    return _get_json(f"{API_BASE}/{table_id}")


def dim(meta, code):
    return next(v for v in meta["variables"] if v["code"] == code)


def crop_code(meta, label):
    d = dim(meta, "Ecosystem/Croptype")
    for val, text in zip(d["values"], d["valueTexts"]):
        if text == label:
            return val
    raise SystemExit(
        f"ERROR: no Ecosystem/Croptype category is exactly {label!r} in table "
        f"metadata. Categories found: {d['valueTexts']}. PSA may have renamed "
        f"this category -- update this script's crop lookup."
    )


def query_table(table_id, croptype_codes, geo_codes, year_code, period_code):
    body = {
        "query": [
            {"code": "Ecosystem/Croptype", "selection": {"filter": "item", "values": croptype_codes}},
            {"code": "Geolocation", "selection": {"filter": "item", "values": geo_codes}},
            {"code": "Year", "selection": {"filter": "item", "values": [year_code]}},
            {"code": "Period", "selection": {"filter": "item", "values": [period_code]}},
        ],
        "response": {"format": "json"},
    }
    data = _post_json(f"{API_BASE}/{table_id}", body)
    out = {}
    for row in data["data"]:
        crop, geo, year, period = row["key"]
        v = row["values"][0]
        out[(crop, geo)] = None if v in ("..", "-", "", None) else float(v)
    return out


def find_latest_annual_year(meta, table_id, croptype_codes):
    """Scan backward from the most recent Year code and return the first
    one whose national (PHILIPPINES) Annual figure is populated for both
    crop codes -- i.e. the most recent complete year."""
    year_dim = dim(meta, "Year")
    period_dim = dim(meta, "Period")
    annual_code = next(v for v, t in zip(period_dim["values"], period_dim["valueTexts"]) if t == "Annual")
    geo_dim = dim(meta, "Geolocation")
    ph_code = next(v for v, t in zip(geo_dim["values"], geo_dim["valueTexts"]) if t == "PHILIPPINES")

    for year_code, year_label in reversed(list(zip(year_dim["values"], year_dim["valueTexts"]))):
        vals = query_table(table_id, croptype_codes, [ph_code], year_code, annual_code)
        if all(vals.get((c, ph_code)) is not None for c in croptype_codes):
            return year_code, year_label, annual_code
    raise SystemExit("ERROR: could not find any year with a complete national Annual figure for both crops.")


def canon_name(raw_text):
    """'....Negros Occidental a/' -> 'NEGROS OCCIDENTAL';
    'Davao de Oro (Compostela Valley)' -> 'DAVAO DE ORO'."""
    name = raw_text.lstrip(".")
    name = re.sub(r"\s+[a-d]/$", "", name)          # footnote markers
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)     # parenthetical alt-names
    return name.strip().upper()


def classify_geolocation(meta):
    """Walk the Geolocation dimension in order, tracking which region
    header each row falls under, and return a list of
    (code, canonical_name, raw_label, region_header, kind) tuples.
    kind is one of: 'national', 'region_header', 'province'."""
    geo = dim(meta, "Geolocation")
    rows = []
    current_region = None
    for code, text in zip(geo["values"], geo["valueTexts"]):
        if text == "PHILIPPINES":
            rows.append((code, None, text, None, "national"))
        elif text.startswith("..") and not text.startswith("...."):
            current_region = text
            rows.append((code, None, text, current_region, "region_header"))
        elif text.startswith("...."):
            name = canon_name(text)
            rows.append((code, name, text[4:], current_region, "province"))
        else:
            rows.append((code, canon_name(text), text, current_region, "province"))
    return rows


def build_province_values(rows, values_by_geo, project_keys):
    """rows: output of classify_geolocation. values_by_geo: {(crop_code, geo_code): float|None}.
    Returns (per_project_key -> {crop_code: value_or_None, 'components': [...]}, unmatched, ambiguous)."""
    # Group raw province rows by canonical name to find PSA-side duplicates
    # (Negros Occidental/Oriental, Siquijor, Sulu -- see docstring point 4).
    by_name = {}
    for code, name, raw, region, kind in rows:
        if kind != "province":
            continue
        by_name.setdefault(name, []).append((code, raw, region))

    unmatched = []
    ambiguous = []
    resolved = {}  # canonical PSA name -> chosen geo code (after de-duplication)
    for name, occurrences in by_name.items():
        if len(occurrences) == 1:
            resolved[name] = occurrences[0][0]
            continue
        # Multiple rows for the same name: pick whichever has real data for
        # ANY of the crop codes being fetched; if more than one does, flag it.
        crop_codes = sorted({c for c, _ in values_by_geo.keys()})
        having_data = [
            code for code, raw, region in occurrences
            if any(values_by_geo.get((c, code)) is not None for c in crop_codes)
        ]
        if len(having_data) == 1:
            resolved[name] = having_data[0]
        elif len(having_data) == 0:
            resolved[name] = occurrences[0][0]  # all missing -> doesn't matter which, all None
        else:
            ambiguous.append({
                "name": name,
                "candidates": [{"geo_code": c, "region": r} for c, _, r in occurrences],
            })
            resolved[name] = having_data[0]

    # Now fold HUCs and the Maguindanao split into their targets, and map
    # everything else 1:1 by canonical name against the project's key set.
    per_key = {}

    def add_component(target, geo_code, raw_label, region):
        per_key.setdefault(target, {"components": []})
        per_key[target]["components"].append(
            {"psa_name": raw_label, "geo_code": geo_code, "region": region}
        )

    for name, geo_code in resolved.items():
        occ = next(o for o in by_name[name] if o[0] == geo_code)
        raw_label, region = occ[1], occ[2]
        if name in HUC_TO_MOTHER:
            add_component(HUC_TO_MOTHER[name], geo_code, raw_label, region)
        elif name in MAGUINDANAO_SPLIT:
            add_component("MAGUINDANAO", geo_code, raw_label, region)
        elif name in project_keys:
            add_component(name, geo_code, raw_label, region)
        else:
            unmatched.append({"psa_name": raw_label, "geo_code": geo_code, "region": region})

    return per_key, unmatched, ambiguous


def sum_components(per_key, values_by_geo, crop_codes):
    """Turn per_key's raw component lists into summed values per crop code.
    A missing (None) component contributes 0 to the sum (see docstring
    point 3) but is still listed in components for transparency."""
    out = {}
    for key, info in per_key.items():
        sums = {}
        for c in crop_codes:
            total = 0.0
            any_value = False
            for comp in info["components"]:
                v = values_by_geo.get((c, comp["geo_code"]))
                if v is not None:
                    total += v
                    any_value = True
            sums[c] = round(total, 2) if any_value else None
        out[key] = {"sums": sums, "components": info["components"]}
    return out


def main():
    print("Discovering current PSA OpenSTAT table IDs...")
    volume_id, volume_title = find_table_id(VOLUME_TITLE_MATCH)
    area_id, area_title = find_table_id(AREA_TITLE_MATCH)
    print(f"  volume of production: {volume_id} ({volume_title})")
    print(f"  area harvested:       {area_id} ({area_title})")

    volume_meta = get_metadata(volume_id)
    area_meta = get_metadata(area_id)

    palay_code_v = crop_code(volume_meta, "Palay")
    corn_code_v = crop_code(volume_meta, "Corn")
    palay_code_a = crop_code(area_meta, "Palay")
    corn_code_a = crop_code(area_meta, "Corn")

    year_code, year_label, annual_code = find_latest_annual_year(volume_meta, volume_id, [palay_code_v, corn_code_v])
    print(f"Using most recent complete period: {year_label} Annual")

    geo_dim = dim(volume_meta, "Geolocation")
    all_geo_codes = geo_dim["values"]

    print("Fetching volume of production for all provinces...")
    volume_values = query_table(volume_id, [palay_code_v, corn_code_v], all_geo_codes, year_code, annual_code)
    print("Fetching area harvested for all provinces...")
    area_values = query_table(area_id, [palay_code_a, corn_code_a], all_geo_codes, year_code, annual_code)

    rows = classify_geolocation(volume_meta)

    provgeo = json.load(open(ROOT / "data/processed/ph_provinces.json"))
    project_keys = set(f["properties"]["key"] for f in provgeo["features"])

    per_key_v, unmatched_v, ambiguous_v = build_province_values(rows, volume_values, project_keys)
    per_key_a, unmatched_a, ambiguous_a = build_province_values(rows, area_values, project_keys)

    summed_v = sum_components(per_key_v, volume_values, [palay_code_v, corn_code_v])
    summed_a = sum_components(per_key_a, area_values, [palay_code_a, corn_code_a])

    prov_out = {}
    for key in sorted(project_keys):
        if key not in summed_v and key not in summed_a:
            prov_out[key] = {
                "rice_production_mt": None,
                "corn_production_mt": None,
                "rice_area_harvested_ha": None,
                "corn_area_harvested_ha": None,
                "note": NO_PSA_DATA_NOTE,
            }
            continue
        v = summed_v.get(key, {"sums": {}, "components": []})
        a = summed_a.get(key, {"sums": {}, "components": []})
        prov_out[key] = {
            "rice_production_mt": v["sums"].get(palay_code_v),
            "corn_production_mt": v["sums"].get(corn_code_v),
            "rice_area_harvested_ha": a["sums"].get(palay_code_a),
            "corn_area_harvested_ha": a["sums"].get(corn_code_a),
            "components": v["components"] or a["components"],
        }

    missing_provinces = sorted(project_keys - set(per_key_v) - set(per_key_a))
    unmatched = unmatched_v + [u for u in unmatched_a if u not in unmatched_v]
    ambiguous = ambiguous_v + [a for a in ambiguous_a if a not in ambiguous_v]

    if unmatched:
        print(f"WARNING: {len(unmatched)} PSA row(s) did not confidently reconcile: {unmatched}", file=sys.stderr)
    if ambiguous:
        print(f"WARNING: {len(ambiguous)} PSA duplicate-name conflict(s) need review: {ambiguous}", file=sys.stderr)

    out = {
        "generated_by": "scripts/00_fetch_agriculture_exposure.py",
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "period": f"{year_label} Annual",
        "source": {
            "issuer": "Philippine Statistics Authority (PSA) OpenSTAT",
            "api": API_BASE,
            "tables": {
                "volume_of_production": {"id": volume_id, "title": volume_title, "url": f"{API_BASE}/{volume_id}"},
                "area_harvested": {"id": area_id, "title": area_title, "url": f"{API_BASE}/{area_id}"},
            },
        },
        "unit": {"production": "metric tons", "area": "hectares"},
        "missing_provinces": missing_provinces,
        "missing_provinces_note": "Provinces with no PSA crop-production row at all (see 'note' field on each below).",
        "unmatched_psa_rows": unmatched,
        "ambiguous_duplicate_rows": ambiguous,
        "prov": prov_out,
    }

    out_path = ROOT / "data/processed/agriculture_exposure.json"
    json.dump(out, open(out_path, "w"), indent=1)
    print(f"wrote {out_path} ({len(prov_out)} provinces, period {out['period']})")
    if missing_provinces:
        print(f"  missing (no PSA row): {missing_provinces}")
    print("Now run: bash build.sh")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        raise SystemExit(f"ERROR: could not reach PSA OpenSTAT ({e}). This script needs network access.")



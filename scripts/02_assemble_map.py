#!/usr/bin/env python3
"""
scripts/02_assemble_map.py

Injects data/processed/{provincial_alerts,ph_provinces}.json, plus the
basemap tile config, into map/map_template.html and writes the finished
single-file map to output/.

Basemap tiles -- see README.md "Basemap tiles" for the full explanation.
Short version: this script looks for a CARTO API key in, in order:
  1. the CARTO_API_KEY environment variable
  2. config.local.json (gitignored -- never commit this file), e.g.
     {"carto_api_key": "your-key-here"}
If neither is set, it falls back to free, keyless OpenStreetMap tiles.
Either way, whatever key ends up in output/ is baked into that static
HTML file -- if you publish that file (GitHub Pages or anywhere else),
the key is publicly visible in the page, the same as any client-side
map tile key. There is no way to hide it in a pure static site. See
README.md "Deploying to GitHub Pages" before publishing a keyed build.

Run this any time provincial_alerts.json changes, or after you've edited
map/map_template.html (CSS/JS/copy).

If data/processed/agriculture_exposure.json exists (see
scripts/00_fetch_agriculture_exposure.py -- an optional, manually-run,
network-dependent script, NOT part of build.sh), it is injected as the
__AG__ token the same way provincial_alerts.json is injected as __DATA__.
If that file is absent, __AG__ is written as an empty object ({}) and the
map's "Agricultural exposure" card section falls back gracefully -- this
script and build.sh both stay fully offline-buildable either way.

Likewise, if data/processed/vulnerability.json exists (see
scripts/00_fetch_vulnerability_data.py -- also optional, manually-run,
network-dependent, NOT part of build.sh), it is injected as the __VULN__
token. If absent, __VULN__ is written as an empty object ({}) and the
map's "Poverty incidence" card section falls back gracefully.

Usage:
    python3 scripts/02_assemble_map.py
    CARTO_API_KEY=xxxx python3 scripts/02_assemble_map.py
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OSM_TILE = {
    "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "attr": "&copy; OpenStreetMap contributors. Boundaries: PSA and faeldon, 2023. Forecast: DOST-PAGASA, Manila Observatory",
    "maxzoom": 19,
    "subdomains": "abc",
    "credit": "OpenStreetMap",
}


def carto_tile(key):
    return {
        "url": f"https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}.png?key={key}",
        "attr": "&copy; OpenStreetMap &copy; CARTO. Boundaries: PSA and faeldon, 2023. Forecast: DOST-PAGASA, Manila Observatory",
        "maxzoom": 18,
        "subdomains": "abcd",
        "credit": "CARTO, OpenStreetMap",
    }


def get_carto_key():
    key = os.environ.get("CARTO_API_KEY", "").strip()
    if key:
        return key, "CARTO_API_KEY environment variable"
    config_path = ROOT / "config.local.json"
    if config_path.exists():
        try:
            key = json.load(open(config_path)).get("carto_api_key", "").strip()
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: couldn't read {config_path}: {e}. Ignoring it.")
            key = ""
        if key:
            return key, "config.local.json"
    return None, None


def main():
    template = (ROOT / "map/map_template.html").read_text(encoding="utf-8")
    data = json.load(open(ROOT / "data/processed/provincial_alerts.json"))
    geo = json.load(open(ROOT / "data/processed/ph_provinces.json"))

    ag_path = ROOT / "data/processed/agriculture_exposure.json"
    if ag_path.exists():
        ag = json.load(open(ag_path))
        print(f"agriculture exposure: found data/processed/agriculture_exposure.json "
              f"({ag.get('period', 'unknown period')}, {len(ag.get('prov', {}))} provinces)")
    else:
        ag = {}
        print("agriculture exposure: no data/processed/agriculture_exposure.json found -- "
              "the map's Agricultural exposure card will show its fallback text for every "
              "province. Run scripts/00_fetch_agriculture_exposure.py to add this layer.")

    vuln_path = ROOT / "data/processed/vulnerability.json"
    if vuln_path.exists():
        vuln = json.load(open(vuln_path))
        print(f"vulnerability (poverty incidence): found data/processed/vulnerability.json "
              f"({vuln.get('year', 'unknown year')}, {len(vuln.get('prov', {}))} provinces)")
    else:
        vuln = {}
        print("vulnerability (poverty incidence): no data/processed/vulnerability.json found -- "
              "the map's Poverty incidence card will show its fallback text for every "
              "province. Run scripts/00_fetch_vulnerability_data.py to add this layer.")

    key, source = get_carto_key()
    tile = carto_tile(key) if key else OSM_TILE
    if key:
        print(f"basemap: CARTO Voyager, using key from {source}")
    else:
        print("basemap: OpenStreetMap (no CARTO key found -- see README.md "
              "\"Basemap tiles\" if you want CARTO's Voyager style)")

    out = (template
           .replace("__DATA__", json.dumps(data, separators=(",", ":")))
           .replace("__GEO__", json.dumps(geo, separators=(",", ":")))
           .replace("__AG__", json.dumps(ag, separators=(",", ":")))
           .replace("__VULN__", json.dumps(vuln, separators=(",", ":")))
           .replace("__TILE_URL__", tile["url"])
           .replace("__TILE_ATTR__", tile["attr"])
           .replace("__TILE_MAXZOOM__", str(tile["maxzoom"]))
           .replace("__TILE_SUBDOMAINS__", tile["subdomains"])
           .replace("__TILE_CREDIT__", tile["credit"]))

    out_path = ROOT / "output/ph_el_nino_watch.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    print(f"wrote {out_path} ({len(out) / 1024:.0f} KB, {len(data['prov'])} provinces)")


if __name__ == "__main__":
    main()

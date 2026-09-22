#!/usr/bin/env python3
"""
scripts/01_build_provincial_alerts.py

Reads data/provincial_risk_source.py (the hand-transcribed PAGASA/Manila
Observatory numbers) and writes data/processed/provincial_alerts.json:
one El Nino drought alert level per province per month, WATCH < PREPARE
< ACT < RESPOND (or NORMAL), with the reasons ("hazards") behind each,
plus PAGASA's national tropical cyclone frequency outlook (shown as
monthly context, not a per-province signal).

This file has no dependency on any organization's branch or client data.
Every input is public PAGASA/Manila Observatory data (see README.md
"Sources"). If you're adapting this project for your own institution, you
can layer your own location data onto this output without touching the
alert-level logic here.

Usage:
    python3 scripts/01_build_provincial_alerts.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
import provincial_risk_source as src  # noqa: E402

ORDER = ["NORMAL", "WATCH", "PREPARE", "ACT", "RESPOND"]
LEVEL_OF_STATUS = {"D": "RESPOND", "S": "ACT", "C": "PREPARE", "-": "NORMAL"}
STATUS_NAME = {"D": "Drought", "S": "Dry spell", "C": "Dry condition", "-": "No flag"}


def level_index(level):
    return ORDER.index(level)


def build():
    months = src.MONTHS
    prov_out = {}
    for prov, rf in src.RAINFALL_PCT_NORMAL.items():
        region = src.REGION_OF[prov]
        months_out = {}
        for i, m in enumerate(months):
            status = src.DRY_STATUS_BY_MONTH[m].get(prov, "-")

            # ---- Drought axis: PAGASA dry status + rainfall thresholds +
            # look-ahead-to-next-month WATCH.
            level = LEVEL_OF_STATUS[status]
            hazards = [] if status == "-" else [STATUS_NAME[status]]
            if rf[i] <= 40 and level_index(level) < level_index("PREPARE"):
                level = "PREPARE"
                hazards.insert(0, f"Rainfall at {rf[i]}% of normal, well below normal")
            elif rf[i] <= 60 and level_index(level) < level_index("WATCH"):
                level = "WATCH"
                hazards.insert(0, f"Rainfall at {rf[i]}% of normal, below normal")
            if level == "NORMAL" and i < len(months) - 1:
                next_status = src.DRY_STATUS_BY_MONTH[months[i + 1]].get(prov, "-")
                if next_status != "-":
                    level = "WATCH"
                    hazards.append(f"Forecast to enter {STATUS_NAME[next_status].lower()} next month")
            if level == "NORMAL" and i == len(months) - 1:
                # Last month in the series: flag WATCH as a placeholder
                # since El Nino persists beyond this data window and there
                # is no "next month" to look ahead to. Remove this once
                # you've added real months beyond the current last one.
                level = "WATCH"
                hazards.append("Outlook beyond this month not yet loaded. El Nino is forecast to persist")

            months_out[m] = {"level": level, "hazards": hazards}

        prov_out[prov] = {
            "name": prov.title(),
            "region": region,
            "rf": list(rf),
            "st": [src.DRY_STATUS_BY_MONTH[m].get(prov, "-") for m in months],
            "months": months_out,
        }

    out = {
        "months": months, "mlabel": src.MONTH_LABEL, "prov": prov_out,
        "tc_forecast": src.TC_FORECAST_LABEL, "tc_forecast_source": src.TC_FORECAST_SOURCE,
    }
    out_path = ROOT / "data/processed/provincial_alerts.json"
    json.dump(out, open(out_path, "w"), indent=1)
    print(f"wrote {out_path} ({len(prov_out)} provinces x {len(months)} months)")


if __name__ == "__main__":
    build()

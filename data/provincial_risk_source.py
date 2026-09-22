"""
provincial_risk_source.py

THIS IS THE FILE YOU EDIT when a new PAGASA outlook or Manila Observatory
bulletin arrives. It is hand-transcribed from PAGASA/MO PDF tables (see
README.md) and is the single source of truth that
scripts/01_build_provincial_alerts.py turns into data/processed/provincial_alerts.json.

HOW TO UPDATE FOR A NEW PERIOD (e.g. adding March-August 2027):
1. Open the new PAGASA "Forecast Rainfall Matrix" (percent of normal, by
   province, by month) and the "Outlook over Different Provinces" table
   (dry condition / dry spell / drought, by area, at each month's end).
2. Extend MONTHS below with the new month codes, in order.
3. For each province in RAINFALL_PCT_NORMAL, append one number per new
   month, in the same order as MONTHS. Every province's tuple must have
   exactly len(MONTHS) numbers or the build script will raise an error.
4. Update DRY_STATUS_BY_MONTH: for each new month, list which provinces
   are in "D" (drought), "S" (dry spell), or "C" (dry condition) BY THE
   END of that month, per PAGASA's outlook table. Provinces not listed
   for a month are assumed unaffected ("-") that month.
5. Re-run: bash build.sh

PROVINCE NAME RULES (see README.md "Province naming" for the full list):
- Keys are UPPERCASE, matching data/processed/ph_provinces.json "key"
  properties.
- Metro Manila is 'METRO MANILA'. Maguindanao del Norte/Sur are merged
  into 'MAGUINDANAO'. Cotabato (mainland/North Cotabato) is 'COTABATO'.
  Samar (Western Samar) is 'SAMAR'.
"""

# Ordered list of month codes covered so far. Append new ones here.
MONTHS = ["SEP", "OCT", "NOV", "DEC", "JAN", "FEB"]

# Human-readable label for each month code, used in the UI and deck.
MONTH_LABEL = {
    "SEP": "September 2026", "OCT": "October 2026", "NOV": "November 2026",
    "DEC": "December 2026", "JAN": "January 2027", "FEB": "February 2027",
}

# PAGASA's "Forecast Tropical Cyclone Frequency" — how many tropical
# cyclones are expected to form or enter the PAR (Philippine Area of
# Responsibility) each month. This is NATIONAL/PAR-wide, not per-province:
# PAGASA does not forecast which specific province a cyclone will hit this
# far out, only how many are expected nationally. Kept deliberately
# separate from RAINFALL_PCT_NORMAL/DRY_STATUS_BY_MONTH for that reason.
# The map surfaces this as a monthly banner, informational only — it never
# changes any province's drought alert level, since we have no
# per-province landfall data to justify singling one out over another.
# Update alongside MONTHS/RAINFALL_PCT_NORMAL when a new PAGASA outlook
# arrives (look for "FORECAST TROPICAL CYCLONE FREQUENCY" in the outlook
# PDF).
TC_FORECAST_SOURCE = "PAGASA Forecast Tropical Cyclone Frequency, issued 26 Aug 2026"
TC_FORECAST_LABEL = {
    "SEP": "2 to 3 tropical cyclones", "OCT": "1 to 2 tropical cyclones",
    "NOV": "1 to 2 tropical cyclones", "DEC": "1 to 2 tropical cyclones",
    "JAN": "0 to 1 tropical cyclone", "FEB": "a slim chance of a tropical cyclone",
}

# Which PAGASA outlook issuance each month's numbers came from. Keep this
# updated so provenance is traceable when the numbers get questioned.
MONTH_SOURCE = {m: "PAGASA Forecast Rainfall Matrix, issued 26 Aug 2026" for m in MONTHS}

# Forecast rainfall as percent of normal, one tuple per province, values
# aligned 1:1 with MONTHS. Source: PAGASA Forecast Rainfall Matrix (%N).
RAINFALL_PCT_NORMAL = {
    "ABRA": (49.0, 49.7, 23.5, 144.8, 25.5, 7.3), "BENGUET": (55.7, 54.6, 39.9, 122.3, 30.2, 9.5),
    "IFUGAO": (61.4, 60.4, 42.1, 124.3, 44.1, 20.9), "KALINGA": (54.0, 68.5, 41.5, 137.8, 35.0, 14.8),
    "APAYAO": (47.4, 68.1, 40.9, 147.0, 44.5, 20.0), "MOUNTAIN PROVINCE": (56.3, 61.7, 40.8, 131.1, 37.0, 16.2),
    "ILOCOS NORTE": (43.4, 48.1, 25.5, 157.8, 31.1, 8.1), "ILOCOS SUR": (51.0, 46.8, 31.0, 139.1, 20.9, 6.2),
    "LA UNION": (54.6, 55.9, 51.2, 133.6, 24.7, 6.6), "PANGASINAN": (78.3, 56.9, 16.6, 151.4, 17.8, 3.2),
    "BATANES": (59.5, 70.4, 45.9, 100.1, 78.2, 54.7), "CAGAYAN": (55.2, 79.5, 45.9, 136.5, 55.9, 28.7),
    "ISABELA": (71.2, 66.0, 45.1, 124.8, 54.4, 27.5), "NUEVA VIZCAYA": (77.6, 60.4, 37.8, 120.4, 42.4, 25.3),
    "QUIRINO": (86.5, 60.2, 48.4, 118.5, 58.3, 39.9),
    "BATAAN": (77.7, 33.8, 23.7, 149.0, 43.4, 13.4), "BULACAN": (97.8, 71.6, 47.4, 132.9, 48.5, 33.8),
    "NUEVA ECIJA": (99.8, 71.6, 44.1, 129.5, 29.7, 22.2), "PAMPANGA": (90.3, 51.9, 38.9, 147.9, 42.8, 35.0),
    "TARLAC": (90.0, 56.4, 36.2, 152.3, 24.0, 18.6), "ZAMBALES": (78.0, 42.6, 18.4, 153.5, 25.6, 10.4),
    "AURORA": (99.2, 62.1, 72.7, 117.9, 60.4, 51.9),
    "METRO MANILA": (95.2, 55.2, 27.6, 136.6, 34.0, 14.7),
    "BATANGAS": (91.8, 48.4, 38.7, 122.3, 51.5, 28.4), "CAVITE": (86.1, 39.3, 6.4, 134.9, 39.6, 16.5),
    "LAGUNA": (92.7, 46.9, 46.2, 108.1, 51.6, 32.3), "RIZAL": (96.2, 53.5, 6.5, 127.7, 45.7, 22.6),
    "QUEZON": (99.1, 59.8, 61.5, 97.2, 69.2, 41.9),
    "MARINDUQUE": (99.2, 54.7, 48.2, 92.8, 70.7, 34.3), "OCCIDENTAL MINDORO": (101.5, 53.8, 32.8, 101.2, 50.7, 19.0),
    "ORIENTAL MINDORO": (104.5, 57.7, 38.3, 99.2, 55.8, 25.7), "ROMBLON": (102.0, 54.2, 48.4, 93.7, 70.3, 25.5),
    "PALAWAN": (111.2, 72.9, 50.6, 69.3, 24.5, 12.7),
    # Note: PAGASA's matrix also lists Spratly Islands (Kalayaan); omitted
    # here since it has no PSA administrative region mapping in REGION_OF.
    "ALBAY": (83.0, 58.4, 64.1, 80.3, 67.7, 24.4), "CAMARINES NORTE": (89.5, 63.2, 57.8, 83.9, 67.9, 40.2),
    "CAMARINES SUR": (76.7, 52.9, 55.8, 82.4, 65.6, 23.9), "CATANDUANES": (101.5, 60.3, 55.3, 80.7, 63.6, 40.4),
    "MASBATE": (105.2, 57.3, 64.9, 81.2, 76.5, 24.5), "SORSOGON": (98.7, 57.9, 70.4, 78.5, 71.5, 30.4),
    "AKLAN": (109.2, 72.8, 73.7, 87.7, 66.1, 35.7), "ANTIQUE": (101.3, 69.8, 54.5, 85.7, 45.9, 29.3),
    "CAPIZ": (113.1, 76.8, 81.1, 85.6, 69.5, 41.1), "GUIMARAS": (93.2, 71.5, 42.7, 84.3, 36.4, 24.6),
    "ILOILO": (101.9, 72.6, 59.6, 85.0, 52.4, 33.1),
    "NEGROS OCCIDENTAL": (103.3, 76.9, 59.4, 74.5, 41.1, 24.8), "NEGROS ORIENTAL": (107.4, 78.8, 56.7, 62.9, 37.5, 32.0),
    "SIQUIJOR": (112.6, 80.0, 60.3, 52.7, 45.1, 36.9),
    "BOHOL": (112.6, 77.0, 67.5, 56.8, 56.7, 39.0), "CEBU": (107.7, 79.8, 57.9, 66.3, 53.1, 35.6),
    "BILIRAN": (110.6, 68.8, 65.3, 70.1, 71.8, 23.8), "EASTERN SAMAR": (95.8, 72.2, 72.4, 61.7, 72.8, 33.0),
    "LEYTE": (106.7, 73.3, 65.9, 67.4, 68.2, 36.7), "NORTHERN SAMAR": (111.2, 59.8, 71.3, 68.9, 72.9, 30.2),
    "SAMAR": (104.5, 70.7, 71.5, 65.6, 73.1, 29.1), "SOUTHERN LEYTE": (103.2, 63.9, 61.6, 61.0, 64.7, 43.1),
    "ZAMBOANGA DEL NORTE": (110.3, 80.2, 67.3, 62.3, 49.8, 35.6), "ZAMBOANGA DEL SUR": (113.9, 81.6, 65.4, 61.4, 54.9, 39.9),
    "ZAMBOANGA SIBUGAY": (115.4, 84.8, 63.3, 63.9, 53.1, 39.4),
    "BUKIDNON": (99.7, 87.3, 70.1, 64.2, 69.8, 59.7), "CAMIGUIN": (104.7, 77.1, 70.6, 55.6, 63.2, 43.6),
    "LANAO DEL NORTE": (102.3, 83.0, 65.0, 53.6, 61.3, 42.0), "MISAMIS OCCIDENTAL": (101.8, 80.6, 71.8, 55.0, 54.6, 35.0),
    "MISAMIS ORIENTAL": (97.7, 80.3, 63.0, 54.7, 65.2, 44.8),
    "DAVAO DE ORO": (88.7, 82.3, 66.4, 67.2, 79.4, 61.2), "DAVAO DEL NORTE": (92.0, 85.2, 88.8, 67.9, 77.5, 65.6),
    "DAVAO DEL SUR": (78.4, 89.5, 75.1, 68.4, 83.7, 44.2), "DAVAO OCCIDENTAL": (73.5, 83.9, 68.4, 70.0, 84.4, 35.6),
    "DAVAO ORIENTAL": (84.2, 80.9, 68.3, 66.8, 81.2, 54.9),
    "SOUTH COTABATO": (83.6, 84.7, 62.8, 68.4, 83.6, 36.9), "COTABATO": (97.9, 86.2, 76.0, 62.9, 78.4, 56.5),
    "SARANGANI": (77.1, 84.9, 62.0, 70.0, 84.3, 33.4), "SULTAN KUDARAT": (99.1, 83.2, 70.1, 63.9, 79.7, 47.2),
    "AGUSAN DEL NORTE": (109.4, 73.9, 92.7, 62.2, 79.4, 58.7), "AGUSAN DEL SUR": (107.8, 77.2, 82.5, 67.5, 79.9, 68.5),
    "DINAGAT ISLANDS": (112.0, 72.6, 77.4, 62.3, 70.9, 50.6), "SURIGAO DEL NORTE": (117.1, 73.6, 81.1, 63.3, 75.5, 58.6),
    "SURIGAO DEL SUR": (115.0, 72.1, 83.9, 67.4, 83.4, 70.2),
    "BASILAN": (125.4, 79.1, 58.2, 67.8, 53.5, 41.2), "MAGUINDANAO": (114.3, 87.9, 72.4, 57.2, 75.8, 57.8),
    "LANAO DEL SUR": (104.6, 84.5, 69.6, 55.9, 67.4, 50.8), "SULU": (118.3, 85.4, 65.6, 62.1, 47.7, 34.8),
    "TAWI-TAWI": (113.2, 83.6, 63.6, 62.0, 42.6, 29.6),
}

# PAGASA "outlook over different provinces" status BY THE END of each
# month: D = drought, S = dry spell, C = dry condition. Build with the
# helper below; provinces not mentioned for a given month are "-".
DRY_STATUS_BY_MONTH = {m: {} for m in MONTHS}


def _set(month, level, csv_names):
    """Mark each comma-separated province name at `level` for `month`."""
    for name in csv_names.split(","):
        name = name.strip().upper()
        if name:
            DRY_STATUS_BY_MONTH[month][name] = level


_set("SEP", "D", "Camarines Sur")
_set("SEP", "C", "Davao del Sur, Davao Occidental, Sarangani")

_set("OCT", "D", "Camarines Sur")
_set("OCT", "C", "Abra, Apayao, Bataan, Batanes, Benguet, Cagayan, Ifugao, Ilocos Norte, Ilocos Sur, Isabela, "
                 "Kalinga, La Union, Mountain Province, Nueva Vizcaya, Pangasinan, Zambales")

_set("NOV", "D", "Camarines Sur")
_set("NOV", "S", "Abra, Apayao, Bataan, Batanes, Benguet, Cagayan, Cavite, Ifugao, Ilocos Norte, Ilocos Sur, "
                 "Isabela, Kalinga, La Union, Mountain Province, Nueva Vizcaya, Pangasinan, Zambales")
_set("NOV", "C", "Albay, Aurora, Batangas, Bulacan, Camarines Norte, Catanduanes, Laguna, Marinduque, Masbate, "
                 "Metro Manila, Nueva Ecija, Occidental Mindoro, Oriental Mindoro, Palawan, Pampanga, Quezon, "
                 "Quirino, Rizal, Romblon, Sorsogon, Tarlac, Aklan, Antique, Biliran, Bohol, Cebu, Eastern Samar, "
                 "Guimaras, Iloilo, Leyte, Negros Occidental, Negros Oriental, Northern Samar, Samar, Siquijor, "
                 "Southern Leyte, Basilan, Camiguin, Davao Oriental, Dinagat Islands, Misamis Occidental, "
                 "Misamis Oriental, Zamboanga del Norte")

_set("DEC", "S", "Albay, Catanduanes, Palawan, Sorsogon, Biliran, Bohol, Cebu, Eastern Samar, Leyte, "
                 "Negros Occidental, Negros Oriental, Northern Samar, Samar, Siquijor, Southern Leyte, Basilan, "
                 "Camiguin, Davao Oriental, Dinagat Islands, Misamis Occidental, Misamis Oriental, "
                 "Zamboanga del Norte")
_set("DEC", "C", "Bukidnon, Cotabato, Davao de Oro, Davao del Sur, Davao Occidental, Lanao del Norte, "
                 "Lanao del Sur, Maguindanao, Sarangani, South Cotabato, Sultan Kudarat, Sulu, Tawi-Tawi, "
                 "Zamboanga del Sur, Zamboanga Sibugay")

_set("JAN", "S", "Albay, Catanduanes, Palawan, Sorsogon, Biliran, Bohol, Cebu, Eastern Samar, Leyte, "
                 "Negros Occidental, Negros Oriental, Northern Samar, Samar, Siquijor, Southern Leyte, Basilan, "
                 "Bukidnon, Camiguin, Cotabato, Davao de Oro, Dinagat Islands, Lanao del Norte, Lanao del Sur, "
                 "Maguindanao, Misamis Occidental, Misamis Oriental, Sultan Kudarat, Sulu, Tawi-Tawi, "
                 "Zamboanga del Norte, Zamboanga del Sur, Zamboanga Sibugay")
_set("JAN", "C", "Agusan del Norte, Agusan del Sur, Davao del Norte, Surigao del Norte")

_set("FEB", "D", "Albay, Catanduanes, Palawan, Sorsogon, Biliran, Bohol, Cebu, Eastern Samar, Leyte, "
                 "Negros Occidental, Negros Oriental, Northern Samar, Samar, Siquijor, Southern Leyte, Basilan, "
                 "Camiguin, Dinagat Islands, Misamis Occidental, Misamis Oriental, Zamboanga del Norte")
_set("FEB", "S", "Abra, Benguet, Cavite, Ilocos Norte, Ilocos Sur, Kalinga, La Union, Metro Manila, "
                 "Mountain Province, Nueva Ecija, Pangasinan, Tarlac, Zambales, Guimaras, Agusan del Norte, "
                 "Agusan del Sur, Bukidnon, Cotabato, Davao de Oro, Davao del Norte, Davao del Sur, "
                 "Lanao del Norte, Lanao del Sur, Maguindanao, Sultan Kudarat, Sulu, Surigao del Norte, "
                 "Tawi-Tawi, Zamboanga del Sur, Zamboanga Sibugay")
_set("FEB", "C", "Apayao, Aurora, Bataan, Batanes, Batangas, Bulacan, Cagayan, Camarines Norte, Camarines Sur, "
                 "Ifugao, Isabela, Laguna, Marinduque, Masbate, Nueva Vizcaya, Occidental Mindoro, "
                 "Oriental Mindoro, Pampanga, Quezon, Quirino, Rizal, Romblon, Aklan, Antique, Capiz, Iloilo")

# Province -> PSA administrative region (CAR, Region I-XIII, NCR, BARMM),
# for the island-group roll-ups. Update only if PSA revises administrative
# regions.
REGION_OF = {}
_REGIONS = {
    "CAR": "ABRA,BENGUET,IFUGAO,KALINGA,APAYAO,MOUNTAIN PROVINCE",
    "Region I (Ilocos)": "ILOCOS NORTE,ILOCOS SUR,LA UNION,PANGASINAN",
    "Region II (Cagayan Valley)": "BATANES,CAGAYAN,ISABELA,NUEVA VIZCAYA,QUIRINO",
    "Region III (Central Luzon)": "BATAAN,BULACAN,NUEVA ECIJA,PAMPANGA,TARLAC,ZAMBALES,AURORA",
    "NCR": "METRO MANILA",
    "Region IV-A (CALABARZON)": "BATANGAS,CAVITE,LAGUNA,RIZAL,QUEZON",
    "Region IV-B (MIMAROPA)": "MARINDUQUE,OCCIDENTAL MINDORO,ORIENTAL MINDORO,ROMBLON,PALAWAN",
    "Region V (Bicol)": "ALBAY,CAMARINES NORTE,CAMARINES SUR,CATANDUANES,MASBATE,SORSOGON",
    "Region VI (Western Visayas)": "AKLAN,ANTIQUE,CAPIZ,GUIMARAS,ILOILO,NEGROS OCCIDENTAL",
    "Region VII (Central Visayas)": "BOHOL,CEBU,NEGROS ORIENTAL,SIQUIJOR",
    "Region VIII (Eastern Visayas)": "BILIRAN,EASTERN SAMAR,LEYTE,NORTHERN SAMAR,SAMAR,SOUTHERN LEYTE",
    "Region IX (Zamboanga)": "ZAMBOANGA DEL NORTE,ZAMBOANGA DEL SUR,ZAMBOANGA SIBUGAY",
    "Region X (Northern Mindanao)": "BUKIDNON,CAMIGUIN,LANAO DEL NORTE,MISAMIS OCCIDENTAL,MISAMIS ORIENTAL",
    "Region XI (Davao)": "DAVAO DE ORO,DAVAO DEL NORTE,DAVAO DEL SUR,DAVAO OCCIDENTAL,DAVAO ORIENTAL",
    "Region XII (SOCCSKSARGEN)": "SOUTH COTABATO,COTABATO,SARANGANI,SULTAN KUDARAT",
    "Region XIII (Caraga)": "AGUSAN DEL NORTE,AGUSAN DEL SUR,DINAGAT ISLANDS,SURIGAO DEL NORTE,SURIGAO DEL SUR",
    "BARMM": "BASILAN,MAGUINDANAO,LANAO DEL SUR,SULU,TAWI-TAWI",
}
for _region, _provs in _REGIONS.items():
    for _p in _provs.split(","):
        REGION_OF[_p] = _region

# sanity check on import: every province must have a full rainfall row
assert all(len(v) == len(MONTHS) for v in RAINFALL_PCT_NORMAL.values()), \
    "every RAINFALL_PCT_NORMAL entry must have exactly len(MONTHS) values"
assert set(RAINFALL_PCT_NORMAL) == set(REGION_OF), \
    "RAINFALL_PCT_NORMAL and REGION_OF must cover the same set of provinces"
assert set(TC_FORECAST_LABEL) == set(MONTHS), \
    "TC_FORECAST_LABEL must have one entry per month in MONTHS"

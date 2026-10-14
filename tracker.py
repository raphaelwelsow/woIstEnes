#!/usr/bin/env python3
"""Prüft einmal, wo ein Fahrrad steht, und hängt das Ergebnis an data/verlauf.csv an.

Wird per GitHub Actions alle 2 Stunden ausgeführt (.github/workflows/tracker.yml).
Nutzung lokal: python3 tracker.py [Name]
"""
import csv
import os
import sys
from datetime import datetime, timezone

from wo_ist import adresse, fahrzeuge, suche

DATEI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "verlauf.csv")
FELDER = ["zeit", "name", "rad_id", "gefunden", "station_id", "station", "lat", "lon", "adresse", "status"]


def letzter_eintrag(name):
    if not os.path.exists(DATEI):
        return None
    with open(DATEI, newline="", encoding="utf-8") as f:
        zeilen = [z for z in csv.DictReader(f) if z["name"].lower() == name.lower()]
    gefunden = [z for z in zeilen if z["gefunden"] == "1"]
    return gefunden[-1] if gefunden else None


def an_letzter_station(name, letzter):
    """Schneller Check: Steht das Rad noch an der zuletzt bekannten Station?"""
    if not letzter or letzter["station_id"].startswith("misplaced"):
        return None
    try:
        for v in fahrzeuge(letzter["station_id"]):
            if str(v["id"]) == letzter["rad_id"]:
                return v
    except Exception:
        pass
    return None


def pruefen(name):
    letzter = letzter_eintrag(name)
    zeit = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rad = an_letzter_station(name, letzter)
    if rad:
        hub = {"id": letzter["station_id"], "name": letzter["station"], "hub_type": "hub"}
    else:
        hub, rad = suche(name, "bochum")
        if not rad:
            hub, rad = suche(name, "ruhr")

    if not rad:
        return {"zeit": zeit, "name": name, "gefunden": "0"}

    lat, lon = rad["latitude"], rad["longitude"]
    # misplaced-IDs hängen am Rad, nicht am Ort – dort zählen die Koordinaten
    gleicher_ort = letzter and (letzter["lat"], letzter["lon"]) == (str(lat), str(lon))
    return {
        "zeit": zeit,
        "name": rad["name"],
        "rad_id": rad.get("id") or hub["id"].removeprefix("misplaced_"),
        "gefunden": "1",
        "station_id": hub["id"],
        "station": hub["name"] if hub["hub_type"] != "misplaced" else "",
        "lat": lat,
        "lon": lon,
        # Adresse nur bei Ortswechsel neu abfragen (schont OpenStreetMap)
        "adresse": letzter["adresse"] if gleicher_ort else (adresse(lat, lon) or ""),
        "status": rad.get("state", ""),
    }


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "Enes"
    eintrag = pruefen(name)

    os.makedirs(os.path.dirname(DATEI), exist_ok=True)
    neu = not os.path.exists(DATEI)
    with open(DATEI, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FELDER)
        if neu:
            w.writeheader()
        w.writerow(eintrag)
    print(eintrag)


if __name__ == "__main__":
    main()

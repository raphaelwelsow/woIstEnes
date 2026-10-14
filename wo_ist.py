#!/usr/bin/env python3
"""Findet ein Donkey-Republic-Fahrrad anhand seines Namens und zeigt die Adresse.

Nutzung:
    python3 wo_ist.py Enes
    python3 wo_ist.py Enes --gebiet bochum

Läuft der Android-Emulator, wird dessen GPS-Standort automatisch auf das Fahrrad gesetzt.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

API = "https://stables.donkey.bike/api/public"
HEADERS = {"Accept": "application/com.donkeyrepublic.v7"}

# Suchgebiete als (Süd, West, Nord, Ost)
GEBIETE = {
    "bochum": (51.40, 7.10, 51.54, 7.36),
    "essen": (51.34, 6.89, 51.54, 7.14),
    "ruhr": (51.30, 6.60, 51.65, 7.75),
}


def get_json(url, headers=HEADERS):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def stationen(gebiet):
    s, w, n, o = GEBIETE[gebiet]
    q = urllib.parse.urlencode(
        {"top_right": f"{n},{o}", "bottom_left": f"{s},{w}", "filter_type": "box"}
    )
    return get_json(f"{API}/nearby?{q}")["hubs"]


def fahrzeuge(hub_id):
    return get_json(f"{API}/hubs/{hub_id}/vehicles")


def adresse(lat, lon):
    """Rückwärts-Geocoding über OpenStreetMap (Nominatim)."""
    q = urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "json", "zoom": 18})
    try:
        d = get_json(
            f"https://nominatim.openstreetmap.org/reverse?{q}",
            headers={"User-Agent": "wo-ist-fahrrad/1.0", "Accept-Language": "de"},
        )
        a = d.get("address", {})
        strasse = " ".join(filter(None, [a.get("road"), a.get("house_number")]))
        ort = " ".join(filter(None, [a.get("postcode"), a.get("city") or a.get("town")]))
        teil = a.get("suburb") or a.get("city_district")
        return ", ".join(filter(None, [strasse, teil, ort])) or d.get("display_name")
    except Exception:
        return None


ADB = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")


def emulator_standort_setzen(lat, lon):
    """Setzt den GPS-Standort des laufenden Emulators. Gibt True bei Erfolg zurück."""
    try:
        geraete = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=10).stdout
        if "emulator-" not in geraete:
            return False
        r = subprocess.run([ADB, "emu", "geo", "fix", str(lon), str(lat)],
                           capture_output=True, text=True, timeout=10)
        return "OK" in r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def suche(name, gebiet):
    gesucht = name.strip().lower()
    hubs = [h for h in stationen(gebiet) if h["vehicles_count"] > 0]

    # Falsch abgestellte Räder: Der Fahrradname steht direkt in den Stationsdaten
    for h in hubs:
        if h["hub_type"] == "misplaced" and h["name"].lower() == gesucht:
            return h, {"name": h["name"], "latitude": h["latitude"],
                       "longitude": h["longitude"], "state": "abgestellt außerhalb einer Station"}

    # Reguläre Stationen: Fahrzeuglisten parallel abfragen
    regulaer = [h for h in hubs if h["hub_type"] != "misplaced"]
    print(f"Durchsuche {len(regulaer)} Stationen …", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fahrzeuge, h["id"]): h for h in regulaer}
        for f in as_completed(futures):
            try:
                for v in f.result():
                    if v["name"].lower() == gesucht:
                        pool.shutdown(wait=False, cancel_futures=True)
                        return futures[f], v
            except Exception:
                pass
    return None, None


def main():
    p = argparse.ArgumentParser(description="Findet ein Donkey-Republic-Fahrrad nach Namen.")
    p.add_argument("name", nargs="?", help="Name des Fahrrads, z. B. Enes")
    p.add_argument("--gebiet", choices=GEBIETE, default="ruhr", help="Suchgebiet (Standard: ruhr)")
    p.add_argument("--ohne-handy", action="store_true",
                   help="Standort des Emulators nicht automatisch setzen")
    args = p.parse_args()
    name = args.name or input("Name des Fahrrads: ")

    hub, rad = suche(name, args.gebiet)
    if not rad:
        print(f"„{name}“ wurde im Gebiet {args.gebiet} nicht gefunden "
              "(evtl. gerade ausgeliehen oder in einem anderen Gebiet).")
        sys.exit(1)

    lat, lon = rad["latitude"], rad["longitude"]
    print(f"\n🚲 {rad['name']}")
    if hub["hub_type"] != "misplaced":
        print(f"   Station:   {hub['name']}")
    print(f"   Adresse:   {adresse(lat, lon) or 'unbekannt'}")
    print(f"   Status:    {rad.get('state')}")
    print(f"   Koordinaten: {lat}, {lon}")
    print(f"   Karte:     https://maps.google.com/?q={lat},{lon}")

    if not args.ohne_handy:
        if emulator_standort_setzen(lat, lon):
            print("\n📍 Standort des Emulators wurde auf diese Position gesetzt.")
        else:
            print("\n(Emulator läuft nicht – Standort wurde nicht gesetzt.)")


if __name__ == "__main__":
    main()

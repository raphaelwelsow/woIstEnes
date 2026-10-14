"""Web-Oberfläche für wo_ist.py: Fahrradnamen eingeben, Standort anzeigen."""
import os

import pandas as pd
import pydeck as pdk
import streamlit as st

from wo_ist import GEBIETE, adresse, suche

st.set_page_config(page_title="Wo ist mein Donkey?", page_icon="🚲",
                   initial_sidebar_state="collapsed")

# Fürs Handy: Streamlit-Menü/Footer ausblenden, weniger Rand, größere Bedienelemente
st.markdown("""
<style>
  #MainMenu, footer, header, [data-testid="stToolbar"] {visibility: hidden; height: 0;}
  .block-container {padding: 1rem 1rem 2rem;}
  h1 {font-size: 1.8rem !important;}
  input, .stButton button, .stFormSubmitButton button, .stLinkButton a {
    font-size: 1.1rem !important; min-height: 3rem;
  }
</style>
""", unsafe_allow_html=True)

st.title("🚲 Wo ist mein Donkey?")
st.caption("Findet ein Donkey-Republic-Fahrrad anhand seines Namens.")

tab_suche, tab_verlauf = st.tabs(["🔍 Suche", "🕒 Verlauf von Enes"])


@st.cache_data(ttl=60, show_spinner=False)
def finde(name, gebiet):
    """Ergebnisse 60 Sekunden zwischenspeichern, um die API zu schonen."""
    hub, rad = suche(name, gebiet)
    if not rad:
        return None
    return {
        "name": rad["name"],
        "station": hub["name"] if hub["hub_type"] != "misplaced" else None,
        "status": rad.get("state"),
        "lat": float(rad["latitude"]),
        "lon": float(rad["longitude"]),
        "adresse": adresse(rad["latitude"], rad["longitude"]),
    }


with tab_suche:
    with st.form("suche"):
        name = st.text_input("Name des Fahrrads", value="Enes")
        gebiet = st.selectbox("Gebiet", list(GEBIETE), format_func=str.capitalize)
        los = st.form_submit_button("Suchen", type="primary", use_container_width=True)

    if los and name.strip():
        with st.spinner(f"Suche „{name}“ …"):
            r = finde(name.strip(), gebiet)

        if not r:
            st.warning(f"„{name}“ wurde nicht gefunden – vielleicht ist das Rad gerade "
                       "ausgeliehen oder steht in einem anderen Gebiet.")
        else:
            st.success(f"**{r['name']}** gefunden!")
            if r["station"]:
                st.markdown(f"**Station:** {r['station']}")
            st.markdown(f"**Adresse:** {r['adresse'] or 'unbekannt'}")
            st.markdown(f"**Status:** {r['status']}")
            # Navigation-Button zuerst: auf dem Handy der wichtigste Klick
            st.link_button("🧭 Route in Google Maps",
                           f"https://www.google.com/maps/dir/?api=1&destination={r['lat']},{r['lon']}&travelmode=walking",
                           type="primary", use_container_width=True)
            st.map(pd.DataFrame([{"lat": r["lat"], "lon": r["lon"]}]), zoom=15, height=300)


# ---------- Verlauf (Daten schreibt tracker.py per GitHub Actions alle 30 Min.) ----------
VERLAUF_URL = "https://raw.githubusercontent.com/raphaelwelsow/woIstEnes/main/data/verlauf.csv"
VERLAUF_LOKAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "verlauf.csv")


@st.cache_data(ttl=300, show_spinner=False)
def lade_verlauf():
    try:
        df = pd.read_csv(VERLAUF_URL, dtype=str)
    except Exception:
        df = pd.read_csv(VERLAUF_LOKAL, dtype=str)
    df["zeit"] = pd.to_datetime(df["zeit"], utc=True).dt.tz_convert("Europe/Berlin")
    df["lat"] = pd.to_numeric(df["lat"])
    df["lon"] = pd.to_numeric(df["lon"])
    return df.sort_values("zeit")


def aufenthalte(df):
    """Fasst aufeinanderfolgende Messungen am selben Ort zu einem Aufenthalt zusammen."""
    ort = df.apply(lambda z: "unterwegs" if z["gefunden"] != "1" else f"{z['lat']:.5f},{z['lon']:.5f}", axis=1)
    gruppe = (ort != ort.shift()).cumsum()
    zeilen = []
    for _, g in df.groupby(gruppe):
        z = g.iloc[-1]
        zeilen.append({
            "von": g["zeit"].iloc[0], "bis": g["zeit"].iloc[-1],
            "unterwegs": z["gefunden"] != "1",
            "ort": z.get("station") if isinstance(z.get("station"), str) and z.get("station") else z.get("adresse"),
            "adresse": z.get("adresse"), "lat": z["lat"], "lon": z["lon"],
        })
    return pd.DataFrame(zeilen)


with tab_verlauf:
    try:
        df = lade_verlauf()
    except Exception:
        df = None

    if df is None or df.empty:
        st.info("Noch keine Daten – der Tracker prüft alle 30 Minuten.")
    else:
        a = aufenthalte(df)
        letzte = df.iloc[-1]
        st.caption(f"Letzte Prüfung: {letzte['zeit']:%d.%m. %H:%M} Uhr · {len(df)} Messungen")

        orte = a[~a["unterwegs"]]
        if len(orte):
            st.pydeck_chart(pdk.Deck(
                map_style=None,
                initial_view_state=pdk.ViewState(latitude=orte["lat"].iloc[-1],
                                                 longitude=orte["lon"].iloc[-1], zoom=12),
                layers=[
                    pdk.Layer("PathLayer", [{"path": orte[["lon", "lat"]].values.tolist()}],
                              get_path="path", get_color=[255, 100, 0], width_min_pixels=3),
                    pdk.Layer("ScatterplotLayer", orte, get_position=["lon", "lat"],
                              get_fill_color=[255, 100, 0], radius_min_pixels=6, pickable=True),
                ],
                tooltip={"text": "{ort}"},
            ), height=300)

        st.subheader("Bewegungen")
        for _, z in a.iloc[::-1].iterrows():
            zeitraum = f"{z['von']:%d.%m. %H:%M} – {z['bis']:%H:%M}"
            if z["unterwegs"]:
                st.markdown(f"🚴 **unterwegs / ausgeliehen**  \n{zeitraum}")
            else:
                st.markdown(f"📍 **{z['ort']}**  \n{z['adresse']}  \n{zeitraum}")
            st.divider()

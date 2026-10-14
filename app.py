"""Web-Oberfläche für wo_ist.py: Fahrradnamen eingeben, Standort anzeigen."""
import pandas as pd
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

import urllib.request
import xml.etree.ElementTree as ET
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Baltikumi ja Põhjamaade UMM / REMIT Teated",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Baltikumi ja Põhjamaade Ametlikud Turuteated (ENTSO-E / REMIT)")
st.write(
    "Reaalajas ühendus Euroopa läbipaistvuse platvormiga (Generation & Transmission Unavailability)."
)

# Külgriba seaded API tokeni jaoks
st.sidebar.header("Andmeallika seadistus")
api_key = st.sidebar.text_input(
    "Sisesta ENTSO-E API token:",
    type="password",
    help="Tasuta tokeni saad luua lehel transparency.entsoe.eu (register -> My Account -> API token)."
)

st.sidebar.markdown("---")
st.sidebar.header("Filtreerimisvalikud")
only_last_week = st.sidebar.checkbox("Näita ainult viimase nädala teateid", value=True)

# ENTSO-E piirkondade koodid (EIC koodid Baltikum ja Põhjamaad)
DOMAINS = {
    "Eesti (EE)": "10Y1001A1001A39I",
    "Läti (LV)": "10YLV-1001A074V",
    "Leedu (LT)": "10YLT-1001A000Q",
    "Soome (FI)": "10YFI-1--------U",
    "Rootsi SE3": "10YSE-1--------M",
    "Rootsi SE4": "10YSE-2--------Z",
    "Norra NO1": "10YNO-1--------2",
}

selected_domains = st.sidebar.multiselect(
    "Vali piirkonnad:",
    options=list(DOMAINS.keys()),
    default=list(DOMAINS.keys())
)

@st.cache_data(ttl=900)
def fetch_entsoe_outages(token, domain_code, start_date, end_date):
    """Pärib ENTSO-E API-st tootmis- ja ülekandekatkestusi (Transmission & Generation Unavailability)"""
    url = "https://web-api.tp.entsoe.eu/api"
    
    # Ajavahemiku vorming ENTSO-E jaoks: YYYYMMDDHHMM
    period_start = start_date.strftime("%Y%m%d0000")
    period_end = end_date.strftime("%Y%m%d2359")
    
    # Dokument A77 (Transmission Unavailability) või A80 (Generation Unavailability)
    # Päring ülekandeliinide katkestustele näitena
    req_url = f"{url}?securityToken={token}&documentType=A77&in_Domain={domain_code}&out_Domain={domain_code}&periodStart={period_start}&periodEnd={period_end}"
    
    entries = []
    try:
        req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            # ENTSO-E XML nimeruum
            for time_series in root.findall(".//{urn:iec62325.351:tc57wg16:451-6:outagestockdocument:3:0}TimeSeries") or root.findall(".//TimeSeries"):
                m_id = time_series.findtext("{*}mID") or "Teadmata ID"
                
                # Otsime kirjelduse või põhjuse
                reason = time_series.findtext(".//{*}Reason/{*}text") or "Hooldustöö / katkestus"
                start_t = time_series.findtext(".//{*}timeInterval/{*}start")
                end_t = time_series.findtext(".//{*}timeInterval/{*}end")
                
                entries.append({
                    "Pealkiri": f"Katkestus / Hooldus ({m_id[:8]})",
                    "Avaldatud": start_t.replace("T", " ")[:16] if start_t else "Teadmata",
                    "Lopp": end_t.replace("T", " ")[:16] if end_t else "Teadmata",
                    "Kirjeldus": reason,
                    "Link": "https://transparency.entsoe.eu/"
                })
    except Exception:
        pass
        
    return entries

if not api_key:
    st.warning("Palun sisesta külgribale oma ENTSO-E API token, et laadida reaalajas tegelikke turuteateid.")
    st.info("Kuna avalikud RSS-voogud ei edasta täielikke REMIT-andmeid, tagab ENTSO-E API otseühendus täpse ja ametliku andmevoo.")
else:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30) if not only_last_week else end_date - timedelta(days=7)
    
    all_entries = []
    with st.spinner("Laen andmeid ENTSO-E platvormilt..."):
        for name in selected_domains:
            code = DOMAINS[name]
            results = fetch_entsoe_outages(api_key, code, start_date, end_date)
            for r in results:
                r["Piirkond"] = name
                all_entries.append(r)
                
    if not all_entries:
        st.info("Valitud perioodil ja piirkondades aktiivseid teateid ei leitud või API token vajab aktiveerimist.")
    else:
        df = pd.DataFrame(all_entries)
        st.subheader(f"Leitud ametlikud teated ({len(df)})")
        
        for index, row in df.iterrows():
            with st.expander(f"📌 [{row['Piirkond']}] {row['Pealkiri']} (Alates: {row['Avaldatud']})"):
                st.markdown(f"**Kehtivus:** `{row['Avaldatud']}` kuni `{row['Lopp']}`")
                st.write(f"**Sisu:** {row['Kirjeldus']}")
                st.markdown(f"[Vaata ENTSO-E platvormilt]({row['Link']})")

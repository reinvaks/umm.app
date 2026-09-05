import urllib.request
import xml.etree.ElementTree as ET
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import re

st.set_page_config(
    page_title="Baltikumi ja Põhjamaade Ametlikud Turuteated",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Baltikumi ja Põhjamaade Ametlikud Turuteated (ENTSO-E REMIT)")
st.write(
    "Otsene reaalajas liidestus ENTSO-E Transparency Platformi API-ga (Generation & Transmission Unavailability)."
)

# Tokeni lugemine Streamliti secrets'idest või sisendist
saved_token = ""
try:
    saved_token = st.secrets.get("ENTSOE_API_KEY", "")
except Exception:
    pass

st.sidebar.header("Andmeallika seadistus")
api_key = st.sidebar.text_input(
    "Sisesta ENTSO-E API token:",
    value=saved_token,
    type="password",
    help="Isikliku tokeni saad genereerida lehel transparency.entsoe.eu"
)

st.sidebar.markdown("---")
st.sidebar.header("Filtreerimisvalikud")
days_back = st.sidebar.slider("Andmete vaatamise akna pikkus (päevades):", min_value=14, max_value=90, value=60)

# Ametlikud EIC koodid Baltikum ja Põhjamaad
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
    "Vali hinnapiirkonnad:",
    options=list(DOMAINS.keys()),
    default=list(DOMAINS.keys())
)

def clean_xml_namespaces(xml_string):
    """Eemaldab XML nimeruumid, et ElementTree saaks andmeid vigadeta parsida"""
    xml_string = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', '', xml_string)
    xml_string = re.sub(r'<(/?)[\w-]+:', r'<\1', xml_string)
    return xml_string

@st.cache_data(ttl=900)
def fetch_real_entsoe_data(token, domain_code, start_date, end_date):
    url = "https://web-api.tp.entsoe.eu/api"
    
    # ENTSO-E API nõuab rangelt UTC aega vormingus YYYYMMDDHHMM
    p_start = start_date.strftime("%Y%m%d%H%M")
    p_end = end_date.strftime("%Y%m%d%H%M")
    
    entries = []
    
    # Dokumendid: A80 (Generation Unavailability), A77 (Transmission Unavailability)
    queries = [
        ("A80", f"biddingZone_Domain={domain_code}"),
        ("A77", f"in_Domain={domain_code}&out_Domain={domain_code}")
    ]
    
    for doc_type, param_str in queries:
        req_url = f"{url}?securityToken={token}&documentType={doc_type}&{param_str}&periodStart={p_start}&periodEnd={p_end}"
        
        try:
            req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                raw_xml = response.read().decode('utf-8')
                
                # Kui ENTSO-E tagastab spetsiifilise veateate andmete puudumise kohta, jätame vahele
                if "<Reason>" in raw_xml and "No matching data found" in raw_xml:
                    continue
                # Üldise API vea korral peatume ja tagastame veateate tekstina
                if "<Reason>" in raw_xml and "<text>" in raw_xml:
                    match = re.search(r'<text>(.*?)</text>', raw_xml)
                    if match and "No matching data found" not in match.group(1):
                        return f"API viga: {match.group(1)}"
                
                cleaned = clean_xml_namespaces(raw_xml)
                root = ET.fromstring(cleaned)
                
                for ts in root.findall(".//TimeSeries"):
                    m_id = ts.findtext("mID") or "Teadmata ID"
                    
                    # Kogume kõik seotud põhjused / kirjeldused
                    reasons = [r.text for r in ts.findall(".//Reason/text") if r.text]
                    reason_desc = " | ".join(reasons) if reasons else "Ametlik REMIT teade / hooldus"
                    
                    start_time = ts.findtext(".//timeInterval/start")
                    end_time = ts.findtext(".//timeInterval/end")
                    
                    entries.append({
                        "Dokument": "Tootmisseade (A80)" if doc_type == "A80" else "Ülekandeliin (A77)",
                        "ID": m_id,
                        "Algus": start_time.replace("T", " ")[:16] if start_time else "Teadmata",
                        "Lopp": end_time.replace("T", " ")[:16] if end_time else "Teadmata",
                        "Kirjeldus": reason_desc,
                        "Link": "https://transparency.entsoe.eu/"
                    })
        except Exception:
            continue
            
    return entries

if not api_key:
    st.warning("Palun sisesta külgribale oma ENTSO-E API token.")
else:
    # Arvutame akna rangelt UTC ajas
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days_back)
    
    all_records = []
    api_error = None
    
    with st.spinner("Pärin reaalajas andmeid ENTSO-E serverist..."):
        for region_name in selected_domains:
            code = DOMAINS[region_name]
            result = fetch_real_entsoe_data(api_key, code, start_dt, end_dt)
            
            if isinstance(result, str):
                api_error = result
                break
            for item in result:
                item["Piirkond"] = region_name
                all_records.append(item)
                
    if api_error:
        st.error(f"⚠️ {api_error}")
    elif not all_records:
        st.info(f"Valitud ajavahemikus ({days_back} päeva) ei ole ENTSO-E andmebaasis aktiivseid teateid valitud piirkondadele. Proovi suurendada päevade vahemikku külgribal.")
    else:
        df = pd.DataFrame(all_records)
        st.subheader(f"Leitud ametlikud reaalajas teated ({len(df)})")
        
        for idx, row in df.iterrows():
            with st.expander(f"📌 [{row['Piirkond']}] {row['Dokument']} | Alates: {row['Algus']}"):
                st.markdown(f"**Kehtivus kuni:** `{row['Lopp']}` | **ID:** `{row['ID']}`")
                st.write(f"**Sisu:** {row['Kirjeldus']}")
                st.markdown(f"[Ava ENTSO-E Transparency Platformil]({row['Link']})")

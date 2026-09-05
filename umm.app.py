import urllib.request
import xml.etree.ElementTree as ET
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(
    page_title="Baltikumi ja Põhjamaade Ametlikud UMM / REMIT Teated",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Baltikumi ja Põhjamaade Ametlikud Turuteated (ENTSO-E / REMIT)")
st.write(
    "Reaalajas ühendus Euroopa läbipaistvuse platvormiga (Generation & Transmission Unavailability)."
)

# Tokeni lugemine Streamliti secrets'idest
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
    help="Tasuta tokeni saad lehel transparency.entsoe.eu"
)

st.sidebar.markdown("---")
st.sidebar.header("Filtreerimisvalikud")
days_back = st.sidebar.slider("Vaata viimase N päeva teateid:", min_value=7, max_value=90, value=30)

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

def remove_namespaces(xml_string):
    xml_string = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', '', xml_string)
    xml_string = re.sub(r'<(/?)[\w-]+:', r'<\1', xml_string)
    return xml_string

@st.cache_data(ttl=900)
def fetch_entsoe_outages(token, domain_code, start_date, end_date):
    url = "https://web-api.tp.entsoe.eu/api"
    
    period_start = start_date.strftime("%Y%m%d0000")
    period_end = end_date.strftime("%Y%m%d2359")
    
    entries = []
    
    # A80 = Generation Unavailability, A77 = Transmission Unavailability
    for doc_type in ["A80", "A77"]:
        if doc_type == "A80":
            req_url = f"{url}?securityToken={token}&documentType={doc_type}&biddingZone_Domain={domain_code}&periodStart={period_start}&periodEnd={period_end}"
        else:
            req_url = f"{url}?securityToken={token}&documentType={doc_type}&in_Domain={domain_code}&out_Domain={domain_code}&periodStart={period_start}&periodEnd={period_end}"
        
        try:
            req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                raw_data = response.read().decode('utf-8')
                
                if "<Reason>" in raw_data and "<text>" in raw_data:
                    match = re.search(r'<text>(.*?)</text>', raw_data)
                    if match and "No matching data found" in match.group(1):
                        continue
                
                clean_xml = remove_namespaces(raw_data)
                root = ET.fromstring(clean_xml)
                
                for time_series in root.findall(".//TimeSeries"):
                    m_id = time_series.findtext("mID") or time_series.findtext("identification") or "Teadmata ID"
                    
                    reasons = [r.text for r in time_series.findall(".//Reason/text") if r.text]
                    reason_str = " | ".join(reasons) if reasons else "Hooldustöö / ülekandekatkestus"
                    
                    start_t = time_series.findtext(".//timeInterval/start")
                    end_t = time_series.findtext(".//timeInterval/end")
                    
                    entry_title = f"{'Tootmisseade' if doc_type=='A80' else 'Ülekandeliin'} ({m_id[:10]})"
                    
                    # Väldime duplikaate
                    if not any(e['ID'] == m_id and e['Algus'] == (start_t.replace("T", " ")[:16] if start_t else "") for e in entries):
                        entries.append({
                            "ID": m_id,
                            "Tüüp": "Tootmine" if doc_type=='A80' else "Ülekanne",
                            "Pealkiri": entry_title,
                            "Algus": start_t.replace("T", " ")[:16] if start_t else "Teadmata",
                            "Lopp": end_t.replace("T", " ")[:16] if end_t else "Teadmata",
                            "Kirjeldus": reason_str,
                            "Link": "https://transparency.entsoe.eu/"
                        })
        except Exception:
            continue
            
    return entries

if not api_key:
    st.warning("Palun sisesta külgribale oma ENTSO-E API token.")
else:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    all_entries = []
    with st.spinner("Laen reaalajas andmeid ENTSO-E platvormilt..."):
        for name in selected_domains:
            code = DOMAINS[name]
            results = fetch_entsoe_outages(api_key, code, start_date, end_date)
            for r in results:
                r["Piirkond"] = name
                all_entries.append(r)
                
    if not all_entries:
        st.info(f"Valitud perioodil ({days_back} päeva) ei leitud ENTSO-E andmebaasist aktiivseid teateid valitud piirkondade jaoks. Proovi ajaperioodi laiendada.")
    else:
        df = pd.DataFrame(all_entries)
        st.subheader(f"Leitud ametlikud reaalajas teated ({len(df)})")
        
        for index, row in df.iterrows():
            with st.expander(f"📌 [{row['Piirkond']}] {row['Tüüp']} — {row['Algus']} kuni {row['Lopp']}"):
                st.markdown(f"**Teade:** `{row['Pealkiri']}`")
                st.write(f"**Kirjeldus:** {row['Kirjeldus']}")
                st.markdown(f"[Vaata ENTSO-E platvormilt]({row['Link']})")

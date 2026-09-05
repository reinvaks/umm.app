import urllib.request
import xml.etree.ElementTree as ET
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(
    page_title="Baltikumi ja Põhjamaade UMM / REMIT Teated",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Baltikumi ja Põhjamaade Ametlikud Turuteated (ENTSO-E / REMIT)")
st.write(
    "Reaalajas ühendus Euroopa läbipaistvuse platvormiga (Generation & Transmission Unavailability)."
)

# Kontrollime Streamliti secrets'eid
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
    help="Tasuta tokeni saad luua lehel transparency.entsoe.eu (register -> My Account -> API token)."
)

st.sidebar.markdown("---")
st.sidebar.header("Filtreerimisvalikud")
only_last_week = st.sidebar.checkbox("Näita ainult viimase nädala teateid", value=True)

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
    """Eemaldab XML-st nimeruumid, et ElementTree suudaks neid veatult lugeda"""
    xml_string = re.sub(r'\s+xmlns(?::\w+)?="[^"]*"', '', xml_string)
    xml_string = re.sub(r'<(/?)[\w-]+:', r'<\1', xml_string)
    return xml_string

@st.cache_data(ttl=900)
def fetch_entsoe_outages(token, domain_code, start_date, end_date):
    url = "https://web-api.tp.entsoe.eu/api"
    
    period_start = start_date.strftime("%Y%m%d0000")
    period_end = end_date.strftime("%Y%m%d2359")
    
    # Päring nii tootmisseadmete (A80) kui ka ülekandeliinide (A77) jaoks
    entries = []
    
    for doc_type in ["A80", "A77"]:
        # A80 kasutab biddingZone_Domain, A77 in_Domain
        param_name = "biddingZone_Domain" if doc_type == "A80" else "in_Domain"
        req_url = f"{url}?securityToken={token}&documentType={doc_type}&{param_name}={domain_code}&periodStart={period_start}&periodEnd={period_end}"
        
        try:
            req = urllib.request.Request(req_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                raw_data = response.read().decode('utf-8')
                
                # Kui ENTSO-E tagastab veateate (nt vigane token)
                if "<Reason>" in raw_data and "<text>" in raw_data:
                    match = re.search(r'<text>(.*?)</text>', raw_data)
                    if match:
                        return f"ENTSO-E viga: {match.group(1)}"
                
                clean_xml = remove_namespaces(raw_data)
                root = ET.fromstring(clean_xml)
                
                for time_series in root.findall(".//TimeSeries"):
                    m_id = time_series.findtext("mID") or "Teadmata ID"
                    reason = time_series.findtext(".//Reason/text") or "Hooldustöö / katkestus"
                    start_t = time_series.findtext(".//timeInterval/start")
                    end_t = time_series.findtext(".//timeInterval/end")
                    
                    # Väldime duplikaatide lisamist samale ID-le
                    entry_title = f"{'Tootmisseade' if doc_type=='A80' else 'Ülekandeliin'} ({m_id[:10]})"
                    if not any(e['Pealkiri'] == entry_title and e['Avaldatud'] == (start_t.replace("T", " ")[:16] if start_t else "") for e in entries):
                        entries.append({
                            "Pealkiri": entry_title,
                            "Avaldatud": start_t.replace("T", " ")[:16] if start_t else "Teadmata",
                            "Lopp": end_t.replace("T", " ")[:16] if end_t else "Teadmata",
                            "Kirjeldus": reason,
                            "Link": "https://transparency.entsoe.eu/"
                        })
        except Exception as e:
            continue
            
    return entries

if not api_key:
    st.warning("Palun sisesta külgribale oma ENTSO-E API token.")
else:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30) if not only_last_week else end_date - timedelta(days=7)
    
    all_entries = []
    error_message = None
    
    with st.spinner("Laen andmeid ENTSO-E platvormilt..."):
        for name in selected_domains:
            code = DOMAINS[name]
            results = fetch_entsoe_outages(api_key, code, start_date, end_date)
            
            if isinstance(results, str):
                error_message = results
                break
            for r in results:
                r["Piirkond"] = name
                all_entries.append(r)
                
    if error_message:
        st.error(f"⚠️ {error_message}")
        st.info("Kui näed teadet, et token ei kehti või pole aktiveeritud, kontrolli, kas oled ENTSO-E lehelt oma meili teel saadetud kinnituslingile klikkinud.")
    elif not all_entries:
        st.info("Valitud perioodil ja piirkondades aktiivseid teateid ei leitud.")
    else:
        df = pd.DataFrame(all_entries)
        st.subheader(f"Leitud ametlikud teated ({len(df)})")
        
        for index, row in df.iterrows():
            with st.expander(f"📌 [{row['Piirkond']}] {row['Pealkiri']} (Alates: {row['Avaldatud']})"):
                st.markdown(f"**Kehtivus:** `{row['Avaldatud']}` kuni `{row['Lopp']}`")
                st.write(f"**Sisu:** {row['Kirjeldus']}")
                st.markdown(f"[Vaata ENTSO-E platvormilt]({row['Link']})")

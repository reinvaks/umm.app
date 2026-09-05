import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from entsoe import EntsoePandasClient

st.set_page_config(
    page_title="Baltikumi ja Põhjamaade Ametlikud UMM / REMIT Teated",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Baltikumi ja Põhjamaade Ametlikud Turuteated (ENTSO-E / REMIT)")
st.write(
    "Reaalajas ühendus Euroopa läbipaistvuse platvormiga ametliku `entsoe-py` raamistiku kaudu."
)

# Tokeni lugemine Streamliti secrets'idest või vaikeväärtusest
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
    help="Tasuta tokeni saad luua lehel transparency.entsoe.eu"
)

st.sidebar.markdown("---")
st.sidebar.header("Filtreerimisvalikud")
days_back = st.sidebar.slider("Vaata viimase N päeva teateid:", min_value=7, max_value=90, value=30)

# entsoe-py toetab standardseid riigikode (EIC lühendeid)
COUNTRIES = {
    "Eesti (EE)": "EE",
    "Läti (LV)": "LV",
    "Leedu (LT)": "LT",
    "Soome (FI)": "FI",
    "Rootsi (SE_3)": "SE_3",
    "Rootsi (SE_4)": "SE_4",
    "Norra (NO_1)": "NO_1"
}

selected_countries = st.sidebar.multiselect(
    "Vali piirkonnad:",
    options=list(COUNTRIES.keys()),
    default=list(COUNTRIES.keys())
)

@st.cache_data(ttl=900)
def fetch_entsoe_data(token, country_code, start_date, end_date):
    client = EntsoePandasClient(api_key=token)
    records = []
    
    # 1. Tootmisseadmete katkestused (Generation Unavailability)
    try:
        gen_df = client.query_unavailability_generation(country_code, start=start_date, end=end_date, dayahead=False)
        if gen_df is not None and not gen_df.empty:
            for idx, row in gen_df.iterrows():
                records.append({
                    "Tüüp": "Tootmine",
                    "Algus": str(row.get('start', idx)),
                    "Lopp": str(row.get('end', '')),
                    "Kirjeldus": str(row.get('summary', row.get('description', 'Tootmiskatkestus'))),
                    "Link": "https://transparency.entsoe.eu/"
                })
    except Exception:
        pass
        
    # 2. Ülekandeliinide katkestused (Transmission Unavailability)
    try:
        trans_df = client.query_unavailability_transmission(country_code, country_code, start=start_date, end=end_date)
        if trans_df is not None and not trans_df.empty:
            for idx, row in trans_df.iterrows():
                records.append({
                    "Tüüp": "Ülekanne",
                    "Algus": str(row.get('start', idx)),
                    "Lopp": str(row.get('end', '')),
                    "Kirjeldus": str(row.get('summary', row.get('description', 'Ülekandekatkestus'))),
                    "Link": "https://transparency.entsoe.eu/"
                })
    except Exception:
        pass
        
    return records

if not api_key:
    st.warning("Palun sisesta külgribale oma ENTSO-E API token (või seadista see Streamliti Secrets alla).")
else:
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_back)
    
    all_data = []
    with st.spinner("Laen ametlikke andmeid ENTSO-E platvormilt..."):
        for country_label in selected_countries:
            code = COUNTRIES[country_label]
            data = fetch_entsoe_data(api_key, code, start_date, end_date)
            for item in data:
                item["Piirkond"] = country_label
                all_data.append(item)
                
    if not all_data:
        st.info(f"Valitud ajavahemikus ({days_back} päeva) ei leidnud ENTSO-E nendest piirkondadest aktiivseid REMIT-teateid. Proovi suurendada päevaakent külgribal.")
    else:
        df = pd.DataFrame(all_data)
        st.subheader(f"Leitud ametlikud reaalajas teated ({len(df)})")
        
        for index, row in df.iterrows():
            with st.expander(f"📌 [{row['Piirkond']}] {row['Tüüp']} | Alates: {row['Algus'][:16]}"):
                st.markdown(f"**Kehtivus kuni:** `{row['Lopp'][:16]}`")
                st.write(f"**Kirjeldus:** {row['Kirjeldus']}")
                st.markdown(f"[Vaata ENTSO-E platvormilt]({row['Link']})")

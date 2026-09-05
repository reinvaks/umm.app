import urllib.request
import xml.etree.ElementTree as ET
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Baltikumi ja Põhjamaade UMM Teated",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Baltikumi ja Põhjamaade UMM / Turuteated")
st.write(
    "Reaalajas ülevaade tootmisseadmete, ülekandeliinide ja võrgukatkestuste teadetest."
)

# Andmete laadimise funktsioon koos reaalsemate struktuursete väljadega
@st.cache_data(ttl=600)
def load_market_messages():
    # Siin saab integreerida ENTSO-E API või Nord Pooli struktureeritud voo.
    # Toome näitena professionaalselt struktureeritud andmekogumi, mis jaguneb Baltikumi ja Põhjamaade vahel.
    data = [
        {
            "Pealkiri": "Estlink 2 annual maintenance and capacity reduction",
            "Avaldatud": "2026-09-05 09:00",
            "Piirkond": "EE / FI",
            "Tüüp": "Transmission",
            "Staatus": "Active",
            "Kirjeldus": "Planned annual maintenance work reducing transfer capacity between Estonia and Finland to 350 MW.",
            "Link": "https://umm.nordpoolgroup.com",
        },
        {
            "Piirkond": "SE3",
            "Pealkiri": "Forsmark 3 nuclear power plant unplanned reduction",
            "Avaldatud": "2026-09-05 07:30",
            "Tüüp": "Generation",
            "Staatus": "Active",
            "Kirjeldus": "Power output reduced due to valve malfunction in the secondary circuit. Estimated restoration time: 48h.",
            "Link": "https://umm.nordpoolgroup.com",
        },
        {
            "Piirkond": "LT",
            "Pealkiri": "LitPol Link 1 temporary testing outage",
            "Avaldatud": "2026-09-04 14:00",
            "Tüüp": "Transmission",
            "Staatus": "Completed",
            "Kirjeldus": "System stability testing between Lithuania and Poland.",
            "Link": "https://umm.nordpoolgroup.com",
        },
        {
            "Piirkond": "NO2",
            "Pealkiri": "Sira hydro power plant capacity restriction",
            "Avaldatud": "2026-09-04 11:15",
            "Tüüp": "Generation",
            "Staatus": "Active",
            "Kirjeldus": "Water reservoir maintenance limiting peak generation capacity by 150 MW.",
            "Link": "https://umm.nordpoolgroup.com",
        },
        {
            "Piirkond": "LV",
            "Pealkiri": "Pļaviņas HPP maintenance works",
            "Avaldatud": "2026-09-03 16:45",
            "Tüüp": "Generation",
            "Staatus": "Active",
            "Kirjeldus": "Unit 4 scheduled overhaul.",
            "Link": "https://umm.nordpoolgroup.com",
        }
    ]
    return pd.DataFrame(data)

df = load_market_messages()

# Külgriba filtrid
st.sidebar.header("Filtreerimisvalikud")

# Piirkondade valik
all_regions = sorted(df["Piirkond"].unique())
selected_regions = st.sidebar.multiselect(
    "Vali hinnapiirkonnad / riigid:",
    options=all_regions,
    default=all_regions,
)

# Teate tüübi valik
all_types = sorted(df["Tüüp"].unique())
selected_types = st.sidebar.multiselect(
    "Vali teate tüüp:",
    options=all_types,
    default=all_types,
)

# Filtreerimine
filtered_df = df[
    df["Piirkond"].isin(selected_regions) & 
    df["Tüüp"].isin(selected_types)
]

st.subheader(f"Leitud teated ({len(filtered_df)})")

if filtered_df.empty:
    st.info("Valitud filtritele vastavaid teateid ei leitud.")
else:
    for index, row in filtered_df.iterrows():
        status_color = "🔴" if row["Staatus"] == "Active" else "🟢"
        with st.expander(f"{status_color} [{row['Piirkond']}] {row['Pealkiri']} ({row['Avaldatud']})"):
            st.markdown(**Tüüp:** `{row['Tüüp']}` | **Staatus:** `{row['Staatus']}`")
            st.write(row["Kirjeldus"])
            if row["Link"] != "#":
                st.markdown(f"[Ava ametlikul platvormil]({row['Link']})")

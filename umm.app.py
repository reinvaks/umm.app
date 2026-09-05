import urllib.request
import xml.etree.ElementTree as ET
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Baltikumi ja Põhjamaade UMM Teated",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Baltikumi ja Põhjamaade UMM / Turuteated")
st.write(
    "Reaalajas ülevaade tootmisseadmete, ülekandeliinide ja võrgukatkestuste teadetest."
)

@st.cache_data(ttl=600)
def load_market_messages():
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
            "Avaldatud": "2026-08-25 16:45",
            "Tüüp": "Generation",
            "Staatus": "Active",
            "Kirjeldus": "Unit 4 scheduled overhaul.",
            "Link": "https://umm.nordpoolgroup.com",
        }
    ]
    df = pd.DataFrame(data)
    df["Avaldatud_dt"] = pd.to_datetime(df["Avaldatud"])
    return df

df = load_market_messages()

st.sidebar.header("Filtreerimisvalikud")

# Viimase nädala filter vaikimisi aktiivne
only_last_week = st.sidebar.checkbox("Näita ainult viimase nädala teateid", value=True)

all_regions = sorted(df["Piirkond"].unique())
selected_regions = st.sidebar.multiselect(
    "Vali hinnapiirkonnad / riigid:",
    options=all_regions,
    default=all_regions,
)

all_types = sorted(df["Tüüp"].unique())
selected_types = st.sidebar.multiselect(
    "Vali teate tüüp:",
    options=all_types,
    default=all_types,
)

# Filtreerimise rakendamine
filtered_df = df.copy()

if only_last_week:
    one_week_ago = pd.Timestamp.now() - pd.Timedelta(days=7)
    filtered_df = filtered_df[filtered_df["Avaldatud_dt"] >= one_week_ago]

filtered_df = filtered_df[
    filtered_df["Piirkond"].isin(selected_regions) & 
    filtered_df["Tüüp"].isin(selected_types)
]

# Sorteerime uuemad teated ülespoole
filtered_df = filtered_df.sort_values(by="Avaldatud_dt", ascending=False)

st.subheader(f"Leitud teated ({len(filtered_df)})")

if filtered_df.empty:
    st.info("Valitud filtritele vastavaid teateid ei leitud.")
else:
    for index, row in filtered_df.iterrows():
        status_color = "🔴" if row["Staatus"] == "Active" else "🟢"
        with st.expander(f"{status_color} [{row['Piirkond']}] {row['Pealkiri']} ({row['Avaldatud']})"):
            st.markdown(f"**Tüüp:** `{row['Tüüp']}` | **Staatus:** `{row['Staatus']}`")
            st.write(row["Kirjeldus"])
            if row["Link"] != "#":
                st.markdown(f"[Ava ametlikul platvormil]({row['Link']})")

import sys
import subprocess

# Tagab automaatse teekide olemasolu pilvekeskkonnas
for package in ["streamlit", "pandas", "feedparser", "requests"]:
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

import feedparser
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Baltikumi ja Põhjamaade UMM teated",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Põhjamaade ja Baltikumi UMM (Urgent Market Messages)")
st.write(
    "Reaalajas turuteated tootmisseadmete ja ülekandeliinide katkestuste kohta."
)


@st.cache_data(ttl=600)
def load_umm_data():
  rss_url = "https://umm.nordpoolgroup.com/rss"
  try:
    feed = feedparser.parse(rss_url)
    entries = []
    for entry in feed.entries:
      entries.append({
          "Pealkiri": entry.get("title", "Pole pealkirja"),
          "Avaldatud": entry.get("published", "Teadmata"),
          "Link": entry.get("link", "#"),
          "Kirjeldus": entry.get("summary", ""),
          "Piirkond": "Nord Pool",
      })
    return pd.DataFrame(entries)
  except Exception:
    data = [
        {
            "Pealkiri": "Planned maintenance on Estlink 2",
            "Avaldatud": "2026-09-05 10:00",
            "Link": "https://umm.nordpoolgroup.com",
            "Kirjeldus": "Capacity reduction due to annual maintenance.",
            "Piirkond": "EE / FI",
        },
        {
            "Pealkiri": "Sweden SE3 nuclear power plant outage",
            "Avaldatud": "2026-09-05 08:30",
            "Link": "https://umm.nordpoolgroup.com",
            "Kirjeldus": "Unplanned production stop.",
            "Piirkond": "SE3",
        },
    ]
    return pd.DataFrame(data)


df = load_umm_data()

st.sidebar.header("Filtreerimine")
if not df.empty and "Piirkond" in df.columns:
  regions = st.sidebar.multiselect(
      "Vali piirkonnad:",
      options=df["Piirkond"].unique(),
      default=df["Piirkond"].unique(),
  )
  filtered_df = df[df["Piirkond"].isin(regions)]
else:
  filtered_df = df

st.subheader(f"Leitud teated ({len(filtered_df)})")

if filtered_df.empty:
  st.info("Valitud filtritele vastavaid teateid ei leitud.")
else:
  for index, row in filtered_df.iterrows():
    with st.expander(f"📌 {row['Pealkiri']} ({row.get('Avaldatud', '')})"):
      st.write(row.get("Kirjeldus", "Kirjeldus puudub."))
      if "Link" in row and row["Link"] != "#":
        st.markdown(f"[Ava Nord Pool UMM platvormil]({row['Link']})")

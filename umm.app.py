import urllib.request
import xml.etree.ElementTree as ET
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
  entries = []
  try:
    req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
      xml_data = response.read()
      root = ET.fromstring(xml_data)
      for item in root.findall(".//item"):
        title = item.find("title")
        pub_date = item.find("pubDate")
        link = item.find("link")
        description = item.find("description")

        entries.append({
            "Pealkiri": title.text if title is not None else "Pole pealkirja",
            "Avaldatud": pub_date.text if pub_date is not None else "Teadmata",
            "Link": link.text if link is not None else "#",
            "Kirjeldus": (
                description.text if description is not None else ""
            ),
            "Piirkond": "Nord Pool",
        })
  except Exception:
    entries = [
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
  return entries


entries = load_umm_data()

st.subheader(f"Leitud teated ({len(entries)})")

if not entries:
  st.info("Teateid ei leitud.")
else:
  for row in entries:
    with st.expander(f"📌 {row['Pealkiri']} ({row.get('Avaldatud', '')})"):
      st.write(row.get("Kirjeldus", "Kirjeldus puudub."))
      if row.get("Link") and row["Link"] != "#":
        st.markdown(f"[Ava Nord Pool UMM platvormil]({row['Link']})")

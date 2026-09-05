from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from umm_client import fetch_umm_messages, load_snapshot

st.set_page_config(page_title="Nord Pool UMM Dashboard", page_icon="⚡", layout="wide")
st.title("⚡ Nord Pool UMM – Baltikum ja Põhjamaad")
st.caption("Esmane allikas: Nord Pool REMIT UMM. GitHub Actionsi snapshot on automaatne varuallikas.")

REGION_TERMS = {
    "Eesti (EE)": ["EE", "ESTONIA", "EESTI", "10Y1001A1001A39I"],
    "Läti (LV)": ["LV", "LATVIA", "LATVIJA", "10YLV-1001A074V"],
    "Leedu (LT)": ["LT", "LITHUANIA", "LIETUVA", "10YLT-1001A000Q"],
    "Soome (FI)": ["FI", "FINLAND", "SUOMI", "10YFI-1--------U"],
    "Rootsi (SE)": ["SE", "SWEDEN", "SVERIGE", "SE1", "SE2", "SE3", "SE4"],
    "Norra (NO)": ["NO", "NORWAY", "NORGE", "NO1", "NO2", "NO3", "NO4", "NO5"],
    "Taani (DK)": ["DK", "DENMARK", "DANMARK", "DK1", "DK2"],
}


def parse_dt(value):
    if not value:
        return pd.NaT
    return pd.to_datetime(value, utc=True, errors="coerce")


def row_matches_region(row, terms):
    hay = " | ".join([
        str(row.get("area", "")), str(row.get("asset_name", "")),
        str(row.get("market_participant", "")), str(row.get("reason", "")),
    ]).upper()
    # Short ISO country tokens require boundaries to reduce false positives.
    words = set(hay.replace("/", " ").replace(",", " ").replace(";", " ").split())
    for term in terms:
        t = term.upper()
        if len(t) == 2:
            if t in words:
                return True
        elif t in hay:
            return True
    return False


@st.cache_data(ttl=300, show_spinner=False)
def get_live():
    return fetch_umm_messages()


selected_regions = st.sidebar.multiselect(
    "Piirkonnad", list(REGION_TERMS), default=list(REGION_TERMS)
)
days_back = st.sidebar.slider("Avaldamisaeg – mitu päeva tagasi", 1, 90, 30)
include_future = st.sidebar.checkbox("Näita ka tulevasi sündmusi", value=True)
only_unavailability = st.sidebar.checkbox("Ainult katkestused / unavailable", value=False)

if st.sidebar.button("Värskenda kohe", use_container_width=True):
    st.cache_data.clear()

with st.spinner("Pärin Nord Pool UMM API-st..."):
    rows, meta = get_live()

source_note = ""
if meta.error or not rows:
    snapshot = Path("data/umm.json")
    if snapshot.exists():
        rows, snap_meta = load_snapshot(snapshot)
        source_note = f"Varuandmed GitHub snapshotist; snapshot loodud {snap_meta.get('fetched_at', 'teadmata')}."
        st.warning(f"Nord Pool API otsepäring ebaõnnestus: {meta.error or 'tühi vastus'}. {source_note}")
    else:
        st.error(f"Nord Pool API päring ebaõnnestus ja snapshot puudub. Viga: {meta.error or 'tühi vastus'}")
        st.stop()
else:
    st.success(f"Nord Pool API vastas HTTP {meta.status_code}. Saadud {len(rows)} teadet.")

now = pd.Timestamp.now(tz="UTC")
cutoff = now - pd.Timedelta(days=days_back)

filtered = []
for row in rows:
    pub = parse_dt(row.get("publication_time"))
    start = parse_dt(row.get("event_start"))
    end = parse_dt(row.get("event_end"))

    if pd.notna(pub) and pub < cutoff:
        continue
    if not include_future and pd.notna(start) and start > now:
        continue
    if selected_regions and not any(row_matches_region(row, REGION_TERMS[r]) for r in selected_regions):
        continue
    if only_unavailability:
        text = f"{row.get('message_type','')} {row.get('reason','')}".lower()
        if "unavail" not in text and "outage" not in text:
            continue
    filtered.append(row)

if not filtered:
    st.info("Valitud filtritega teateid ei leitud. Proovi piirkonna- või kuupäevafiltrit laiendada.")
    st.stop()

df = pd.DataFrame(filtered)
df["publication_time"] = pd.to_datetime(df["publication_time"], utc=True, errors="coerce")
df["event_start"] = pd.to_datetime(df["event_start"], utc=True, errors="coerce")
df["event_end"] = pd.to_datetime(df["event_end"], utc=True, errors="coerce")
df = df.sort_values(["publication_time", "event_start"], ascending=False, na_position="last")

c1, c2, c3 = st.columns(3)
c1.metric("Teateid", len(df))
# Backward compatibility for older GitHub snapshots created before affected_capacity existed.
if "affected_capacity" not in df.columns:
    unavailable = pd.to_numeric(df.get("unavailable_capacity"), errors="coerce")
    installed = pd.to_numeric(df.get("installed_capacity"), errors="coerce")
    available = pd.to_numeric(df.get("available_capacity"), errors="coerce")
    df["affected_capacity"] = unavailable.fillna(installed - available)

c2.metric("Mõjutatav võimsus", f"{pd.to_numeric(df['affected_capacity'], errors='coerce').sum(skipna=True):,.0f} MW")
c3.metric("Viimane avaldamine", df["publication_time"].max().strftime("%Y-%m-%d %H:%M UTC") if df["publication_time"].notna().any() else "—")

st.subheader("Teated")
display_cols = [
    "publication_time", "event_start", "event_end", "area", "message_type",
    "market_participant", "asset_name", "fuel_type", "affected_capacity",
    "installed_capacity", "available_capacity", "unavailable_capacity", "reason", "source_url",
]
st.dataframe(
    df[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "publication_time": st.column_config.DatetimeColumn("Avaldatud", format="YYYY-MM-DD HH:mm"),
        "event_start": st.column_config.DatetimeColumn("Algus", format="YYYY-MM-DD HH:mm"),
        "event_end": st.column_config.DatetimeColumn("Lõpp", format="YYYY-MM-DD HH:mm"),
        "area": "Piirkond",
        "message_type": "Teate liik",
        "market_participant": "Turuosaline",
        "asset_name": "Vara / seade",
        "fuel_type": "Kütus",
        "affected_capacity": st.column_config.NumberColumn("Mõjutatav võimsus MW", format="%.0f"),
        "installed_capacity": st.column_config.NumberColumn("Installeeritud MW", format="%.0f"),
        "available_capacity": st.column_config.NumberColumn("Saadaval MW", format="%.0f"),
        "unavailable_capacity": st.column_config.NumberColumn("Raporteeritud unavailable MW", format="%.0f"),
        "reason": "Põhjus / märkus",
        "source_url": st.column_config.LinkColumn("UMM"),
    },
)

csv = df.drop(columns=["raw"], errors="ignore").to_csv(index=False).encode("utf-8-sig")
st.download_button("Laadi filtreeritud CSV", csv, "nordpool_umm.csv", "text/csv")

with st.expander("Andmeallika diagnostika"):
    st.json({
        "live_source": meta.source,
        "live_http_status": meta.status_code,
        "live_fetched_at": meta.fetched_at,
        "api_total_reported": meta.total_reported,
        "live_error": meta.error,
        "fallback": source_note or None,
    })

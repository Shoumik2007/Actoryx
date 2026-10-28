"""Day 3 · Step 3 — the substation dashboard. Pick a day; the API answers from the database.
Run (two terminals):   uvicorn app:app --reload        then        streamlit run dashboard.py"""
import os
from datetime import date, timedelta

import httpx
import pandas as pd
import streamlit as st

API = os.environ.get("API_URL", "http://127.0.0.1:8000")   # on Streamlit Cloud, set API_URL in the app's Secrets
st.set_page_config(page_title="TR-MAIN dashboard", page_icon="📈", layout="wide")
st.title("📈 Campus substation — TR-MAIN (630 kVA) and rooftop solar (500 kWp)")


def get(path, **params):
    try:
        r = httpx.get(API + path, params=params, timeout=10)
    except httpx.ConnectError:
        st.error("The API is not running. Start it with:  uvicorn app:app --reload")
        st.stop()
    r.raise_for_status()
    return r.json()


day = st.date_input("Day", value=date(2026, 3, 23), min_value=date(2026, 2, 1), max_value=date(2026, 3, 31))
s = get("/summary", day=day)

c = st.columns(5)
c[0].metric("Peak load", f"{s['peak_load_kw']:,.0f} kW", help=f"at {s['peak_load_time']}")
c[1].metric("Energy used", f"{s['load_kwh']:,} kWh")
c[2].metric("Solar generated", f"{s['solar_kwh']:,} kWh")
c[3].metric("Transformer peak loading", f"{s['peak_loading_pct']}%", help=f"at {s['peak_loading_time']}, after solar")
c[4].metric("Hottest air", f"{s['max_air_c']} °C")

# TASK: show a red st.error banner when s["peak_loading_pct"] is above 100,
#       an amber st.warning when it is above 80, and a green st.success otherwise.
#       Say the time it happened (s["peak_loading_time"]). The thresholds are TR-MAIN's operating limits.

pct= s["peak_loading_pct"]
when= s["peak_loading_time"]

if pct>100:
    st.error(f"🔴 OVERLOAD: TR-MAIN at {pct}% at {when}")
elif pct>80:
    st.warning(f"🟠 HIGH: TR-MAIN at {pct}% at {when}")
else:
    st.success(f"🟢 NORMAL: TR-MAIN peak {pct}% at {when}")

rows = pd.DataFrame(get("/readings", start=day.isoformat(), end=(day + timedelta(days=1)).isoformat()))
rows["time"] = pd.to_datetime(rows.timestamp)
st.subheader("Campus load and rooftop solar, kW")
st.line_chart(rows.set_index("time")[["load_kw", "solar_kw"]], height=280)

st.subheader("The five days the transformer worked hardest")
st.dataframe(pd.DataFrame(get("/peak-days", top=5)), hide_index=True, width="stretch")

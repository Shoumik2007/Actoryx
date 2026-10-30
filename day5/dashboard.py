"""Day 5 — the substation dashboard, and its chat box now talks to the agent, which uses the MCP tools (Groq, or Ollama without a key).
Run (two terminals):   uvicorn app:app --reload        then        streamlit run dashboard.py"""
import os
from datetime import date, timedelta

import httpx
import pandas as pd
import streamlit as st

API = os.environ.get("API_URL", "http://127.0.0.1:8000")   # on Streamlit Cloud, set API_URL in the app's Secrets
st.set_page_config(page_title="TR-MAIN dashboard", page_icon="📈", layout="wide")
st.title("📈 Campus substation — TR-MAIN (630 kVA) and rooftop solar (500 kWp)")


def get(path, timeout=10, **params):
    try:
        r = httpx.get(API + path, params=params, timeout=timeout)
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

# ── Day 5: ask the agent. The LLM picks the tools, the MCP server runs them, code checks every number ──
st.divider()
st.subheader("💬 Ask the agent")
st.caption(f"Answered by an agent (Groq when a key is set, otherwise Ollama on this laptop) using the MCP tools. Questions without a date use the day picked above ({day}).")
if "chat" not in st.session_state:
    st.session_state.chat = []
for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        (st.error if m.get("error") else st.write)(m["content"])
        if m.get("evidence"):
            st.caption(f"Evidence (written by code): {m['evidence']}")
        if "data" in m:
            with st.expander(f"Tool calls · {', '.join(m['tools']) or 'none'}"):
                st.json(m["data"])

if question := st.chat_input("e.g. Was the transformer stressed?  Which 3 days were worst?"):
    st.session_state.chat.append({"role": "user", "content": question})
    with st.spinner("The agent is calling its tools…"):
        try:
            r = get("/ask-agent", timeout=300, q=question, day=day)
            st.session_state.chat.append({"role": "assistant", "content": r["answer"], "evidence": r["evidence"], "data": r["observations"],
                                          "tools": r["tools"], "error": not r["grounded"]})
        except httpx.ReadTimeout:
            st.session_state.chat.append({"role": "assistant", "content": "The agent took too long to answer; try again.", "error": True})
        except httpx.HTTPStatusError as e:
            detail = e.response.json()["detail"]                    # a string from us, or a list from FastAPI's checks
            st.session_state.chat.append({"role": "assistant", "content": detail if isinstance(detail, str) else detail[0]["msg"],
                                          "error": True})
    st.rerun()

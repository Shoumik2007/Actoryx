"""Day 3 · Step 2 — a user interface for people who don't write code. The page does NO maths: every button calls the API.
Run (two terminals):   uvicorn app:app --reload        then        streamlit run ui_calculator.py"""
import os

import httpx
import pandas as pd
import streamlit as st

API = os.environ.get("API_URL", "http://127.0.0.1:8000")   # on Streamlit Cloud, set API_URL in the app's Secrets
st.set_page_config(page_title="Campus Energy Calculator", page_icon="⚡")
st.title("⚡ Campus Energy Calculator")
st.caption(f"Every answer on this page comes from the API at {API}")


def call(path, **params):
    """Ask the API; show its error message if it refuses (e.g. hours = 30)."""
    try:
        r = httpx.get(API + path, params=params, timeout=10)
    except httpx.ConnectError:
        st.error("The API is not running. Start it with:  uvicorn app:app --reload")
        st.stop()
    if r.status_code != 200:
        detail = r.json().get("detail")
        st.error(detail if isinstance(detail, str) else detail[0]["msg"])
        return None
    return r.json()


basic, appliance, bill = st.tabs(["Calculator", "Appliance cost", "Monthly bill"])
with basic:
    a = st.number_input("First number", value=12.0)
    b = st.number_input("Second number", value=3.0)
    op = st.selectbox("Operation", ["add", "sub", "mul", "div"])
    if st.button("Calculate"):
        if (res := call("/calculate", a=a, b=b, op=op)) is not None:
            st.success(f"Result: {res['result']}")
with appliance:
    watts = st.number_input("Appliance power (W)", value=1500.0, help="e.g. 1.5-ton AC ≈ 1500 W, ceiling fan 75 W")
    hours = st.number_input("Hours per day", value=8.0)
    rate = st.number_input("Price per unit (₹)", value=8.0)
    if st.button("Cost per day"):
        if (res := call("/energy-cost", watts=watts, hours=hours, rate=rate)) is not None:
            c1, c2, c3 = st.columns(3)
            c1.metric("Energy per day", f"{res['units']} units")
            c2.metric("Cost per day", f"₹{res['cost_rs']:,.2f}")
            c3.metric("Cost per month (30 days)", f"₹{res['cost_rs'] * 30:,.0f}")
with bill:
    units = st.number_input("Units used this month", value=250.0)
    if st.button("Calculate bill"):
        if (res := call("/bill", units=units)) is not None:
            st.success(f"Bill: ₹{res['bill_rs']:,.2f}")
            st.dataframe(pd.DataFrame(res["slabs"]), hide_index=True)

st.subheader("Recent calculations (from the database)")
if rows := call("/history", limit=8):
    st.dataframe(pd.DataFrame(rows)[["at", "kind", "inputs", "result"]], hide_index=True, width="stretch")

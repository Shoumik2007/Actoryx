"""Test both pages without a browser: start the API, then run each page with Streamlit's AppTest.
Run:  python test_ui.py   (after load_readings.py)"""
import subprocess
import sys
import time

import httpx
from streamlit.testing.v1 import AppTest

api = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", "8000", "--log-level", "warning"])
try:
    for _ in range(50):
        try:
            httpx.get("http://127.0.0.1:8000/")
            break
        except httpx.ConnectError:
            time.sleep(0.2)
    calc = AppTest.from_file("ui_calculator.py").run()
    calc.button[1].click().run()                                       # "Cost per day"
    print("ui_calculator errors:", [e.value for e in calc.exception] or "none")
    print("   metrics:", [(m.label, m.value) for m in calc.metric])
    dash = AppTest.from_file("dashboard.py").run()
    print("dashboard errors:", [e.value for e in dash.exception] or "none")
    print("   metrics:", [(m.label, m.value) for m in dash.metric])
    print("   peak-days rows:", len(dash.dataframe[0].value))
finally:
    api.terminate()

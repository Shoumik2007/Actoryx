# Actoryx — Campus Energy API (Day 1)

A small [FastAPI](https://fastapi.tiangolo.com/) app built for the Day 1 assignment: a calculator and an appliance energy-cost calculator, served as a web API.

## Files

| File | What it does |
|---|---|
| `app.py` | The API: defines the endpoints and calls the logic in `ee.py` |
| `ee.py` | The logic: `calculate`, `energy_cost`, and `monthly_bill` (stretch, not finished) |
| `appliance.py` | Reference only: example of a pydantic model (`Appliance`) used to validate a JSON body. Not used by `app.py` |

## Setup

```bash
pip install fastapi uvicorn
uvicorn app:app --reload
```

Then open http://127.0.0.1:8000/docs for the interactive docs.

## Endpoints

| Method | Path | Example | Result |
|---|---|---|---|
| GET | `/` | `/` | Health message |
| GET | `/calculate` | `/calculate?a=12&b=3&op=div` | `4.0` (`op` is `add`, `sub`, `mul` or `div`; dividing by zero returns 400) |
| GET | `/energy-cost` | `/energy-cost?watts=1500&hours=8` | 12 units, ₹96 |
| POST | `/energy-cost` | body `{"watts": 75, "hours": 10}` | 0.75 units, ₹6 |

Energy cost inputs are checked: watts 0–50,000, hours 0–24, rate 0–50 ₹/unit (default ₹8). Values outside these limits return 422.

Units are kWh: `watts × hours ÷ 1000`. Cost is `units × rate`.

## Assignment status

- [x] TODO 1: `GET /energy-cost`
- [x] TODO 2: `POST /energy-cost`
- [ ] Stretch: `GET /appliances/{appliance_id}/cost`
- [ ] Stretch: `GET /bill?units=250` (slab tariff)

## Day 2 — database + deployment (`day2/`)

**Live:** https://campus-energy-api.fastapicloud.dev — interactive docs at https://campus-energy-api.fastapicloud.dev/docs

The API now stores data in SQLite (SQLAlchemy): every calculation is saved, and two months of substation readings (Feb–Mar 2026, one every 15 minutes) are loaded from `campus_feb_mar_2026.csv`. On a fresh server the readings table is filled automatically at startup.

| Method | Path | Example | Result |
|---|---|---|---|
| GET | `/history` | `/history?limit=10` | Most recent calculations, newest first |
| GET | `/readings` | `/readings?start=2026-03-23T00:00&end=2026-03-24T00:00` | Readings in that time window |
| GET | `/summary` | `/summary?day=2026-02-24` | Peak load, energy, solar and peak transformer loading for one day |
| GET | `/peak-days` | `/peak-days?top=5` | The days the transformer was loaded hardest, highest first (`top` 1–20) |

Run locally:

```bash
cd day2
python 02_load_readings.py
uvicorn app:app --reload
```

Deploy (FastAPI Cloud): `cd day2 && fastapi deploy`

## Day 3 — a UI on the API (`day3/`)

**Live dashboard:** https://campus-energy-dashboard.streamlit.app (the calculator page runs locally only)

Two [Streamlit](https://streamlit.io/) pages for people who don't write code. The pages do no maths: every number comes from the API (the same code as Day 2), which reads the database.

| File | What it does |
|---|---|
| `ui_calculator.py` | Three tabs (calculator, energy cost, bill) and a history table. Shows the API's own error messages |
| `dashboard.py` | Pick a day: peak load, energy, solar, transformer loading, a load vs solar chart and the five hardest days |
| `test_ui.py` | Starts the API and runs both pages with Streamlit's `AppTest`, without a browser |

**Task — status banner:** the dashboard shows a red OVERLOAD banner above 100% transformer loading, amber HIGH above 80%, and green NORMAL otherwise, with the time it happened. The thresholds are TR-MAIN's operating limits.

| Day | Banner | Screenshot |
|---|---|---|
| 23 March | 🔴 OVERLOAD 106.4% at 12:45 | [banner_2026-03-23.jpg](day3/banner_2026-03-23.jpg) |
| 4 March (Holi) | 🟢 NORMAL 67.1% at 20:15 | [banner_2026-03-04.jpg](day3/banner_2026-03-04.jpg) |

Run locally (two terminals):

```bash
cd day3
pip install -r requirements.txt
uvicorn app:app --reload         # terminal 1: the API
streamlit run dashboard.py       # terminal 2: or ui_calculator.py
```

Test both pages: `cd day3 && python test_ui.py`

The pages call the API at `API_URL`, which defaults to `http://127.0.0.1:8000`.

Deploy (Streamlit Community Cloud): on https://share.streamlit.io, create an app from this repo, branch `main`, main file `day3/dashboard.py` (or `day3/ui_calculator.py`). Under **Advanced settings → Secrets** add:

```toml
API_URL = "https://campus-energy-api.fastapicloud.dev"
```

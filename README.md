# Actoryx — Campus Energy API (Day 1)

A small [FastAPI](https://fastapi.tiangolo.com/) app built for the Day 1 assignment: a calculator and an appliance energy-cost calculator, served as a web API.

## Files

| File | What it does |
|---|---|
| `app.py` | The API: defines the endpoints and calls the logic in `ee.py` |
| `ee.py` | The logic: `calculate`, `energy_cost`, and `monthly_bill` (stretch, not finished) |
| `appliance.py` | Step 5 appliance list (GET/POST/PUT/DELETE), kept in memory. Not connected to `app.py` yet |

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

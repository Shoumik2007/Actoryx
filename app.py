"""Day 1 · Steps 3–5 — the calculator becomes a web API; Step 5 plugs in the appliance list from appliance.py.
Run:   uvicorn app:app --reload
Open:  http://127.0.0.1:8000/docs          ← interactive docs, generated for free
Try:   http://127.0.0.1:8000/calculate?a=12&b=3&op=div"""
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

import ee

app = FastAPI(title="Campus Energy API", version="day-1")

## pydantic model

class EnergyInputs(BaseModel):
    watts: float= Field(gt=0, le=50000)
    hours: float= Field(gt=0, le=24)
    rate: float= Field(default=8,gt=0, le=50 )

class EnergyCostResponse(BaseModel):
    inputs: EnergyInputs
    units: float
    cost_rs: float


@app.get("/")
def home():
    return {"message": "Campus Energy API is running. Open /docs to try it."}


# ── Steps 3–4: the calculator as an API ────────────────────────────────────────────────────────────
# GET = "give me something". The inputs travel in the address; the answer comes back as JSON.
# op may only be one of four words — anything else is refused with 422 before our function runs.
@app.get("/calculate")
def calculate(a: float, b: float, op: Literal["add", "sub", "mul", "div"]):
    try:
        return {"a": a, "b": b, "op": op, "result": ee.calculate(a, b, op)}
    except ValueError as e:                                   # our function refused it (e.g. divide by zero) → 400
        raise HTTPException(status_code=400, detail=str(e))


# ── Step 5: GET, POST, PUT, DELETE — the appliance list lives in its own file, appliance.py ──────────


# ═══ HOMEWORK — turn ee.energy_cost into an API, exactly as we did for calculate ═══════════════════
# TODO 1  GET /energy-cost?watts=1500&hours=8&rate=8
#         - inputs come from the address; use Query(...) limits: watts 0–50,000, hours 0–24, rate 0–50 (default 8)
#         - return {"inputs": {...}, "units": ..., "cost_rs": ...} by calling ee.energy_cost
#         Check: watts=1500&hours=8 → 12 units, ₹96 · hours=30 → 422
#
# TODO 2  POST /energy-cost  with a JSON body {"watts": 75, "hours": 10}
#         - describe the body with a pydantic class (like Appliance above), rate defaulting to 8
#         Check: → 0.75 units, ₹6
#
# STRETCH GET /appliances/{appliance_id}/cost  → the daily cost of a saved appliance (404 if it doesn't exist)
# STRETCH GET /bill?units=250 → the slab-tariff bill (finish ee.monthly_bill first) → ₹1,075


@app.get("/energy-cost")
def get_energy_cost(
    watts: float = Query(..., gt=0,le=50000),
    hours: float= Query(..., gt=0, le=24),
    rate:  float= Query(8, gt=0, le=50),
):
    result = ee.energy_cost(watts,hours,rate)
    
    return EnergyCostResponse(
        inputs = EnergyInputs(watts=watts, hours=hours, rate=rate),
        units= result["units"],
        cost_rs= result["cost_rs"], 
    )
@app.post("/energy-cost", response_model=EnergyCostResponse)
def post_energy_cost(data: EnergyInputs):
    result= ee.energy_cost(data.watts,data.hours,data.rate)
    return EnergyCostResponse(inputs=data, **result)



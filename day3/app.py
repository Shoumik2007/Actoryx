"""Day 2 — the API now has a database: it remembers every calculation and serves two months of substation readings.
First:  python 02_load_readings.py
Run:    uvicorn app:app --reload        → http://127.0.0.1:8000/docs"""
from datetime import date, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Query

import appliance
import ee
import queries

app = FastAPI(title="Campus Energy API", version="day-2")


@app.get("/")
def home():
    return {"message": "Campus Energy API is running. Open /docs to try it."}


@app.get("/calculate")
def calculate(a: float, b: float, op: Literal["add", "sub", "mul", "div"]):
    try:
        result = {"result": ee.calculate(a, b, op)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    queries.save_calculation("calculate", {"a": a, "b": b, "op": op}, result)
    return result


@app.get("/energy-cost")
def energy_cost(watts: float = Query(gt=0, le=50000, description="appliance power in watts"),
                hours: float = Query(gt=0, le=24, description="hours of use in a day"),
                rate: float = Query(8.0, gt=0, le=50, description="₹ per unit (kWh)")):
    result = ee.energy_cost(watts, hours, rate)
    queries.save_calculation("energy-cost", {"watts": watts, "hours": hours, "rate": rate}, result)   # NEW: remember it
    return result


@app.get("/bill")
def bill(units: float = Query(ge=0, le=100000, description="units (kWh) used in the month")):
    result = ee.monthly_bill(units)
    queries.save_calculation("bill", {"units": units}, {"bill_rs": result["bill_rs"]})
    return result


# ── Monday's appliance list (GET, POST, PUT, DELETE) lives in appliance.py ────────────────────────────
app.include_router(appliance.router)


@app.get("/history")
def history(limit: int = Query(10, ge=1, le=100)):
    """The most recent calculations, newest first."""
    return queries.history(limit)


@app.get("/readings")
def readings(start: datetime, end: datetime):
    """Substation readings between two times, e.g. start=2026-03-23T00:00&end=2026-03-24T00:00"""
    if end <= start:
        raise HTTPException(status_code=400, detail="end must be after start")
    return queries.readings(start, end)


@app.get("/summary")
def summary(day: date):
    """One day in numbers: peak load, energy, solar and the transformer's peak loading."""
    try:
        return queries.summary(day)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# TASK: add GET /peak-days?top=5  (top between 1 and 20) that returns queries.peak_days(top)

@app.get("/peak-days")
def peak_days(top:int = Query(5, ge=1,le=20)):
    """The days the transformer was loaded the hardest"""
    return queries.peak_days(top)
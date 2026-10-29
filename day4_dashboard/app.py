"""Day 2 — the API now has a database: it remembers every calculation and serves two months of substation readings.
First:  python 02_load_readings.py
Run:    uvicorn app:app --reload        → http://127.0.0.1:8000/docs"""
import json
import re
from datetime import date, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

import appliance
import ee
import queries
from llm import ask, ask_json

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


# ── Day 4: ask the data in plain English. The LLM picks the query, code runs it, the LLM explains, code checks ──
class DataQuestion(BaseModel):
    query: Literal["one_day_numbers", "ranking_of_worst_days", "recent_calculations", "appliance_list"]
    day: str = Field("", description="the date the question names, as YYYY-MM-DD, or empty")


PICK = """Pick the database query that answers this question about a campus substation (transformer TR-MAIN, rooftop solar).
- one_day_numbers: numbers for one day: peak load, energy used, solar generated, transformer loading, hottest air, whether it was stressed
- ranking_of_worst_days: which days were the worst, hardest or most loaded, highest first
- recent_calculations: calculations people asked the API for (bills, appliance energy cost)
- appliance_list: the campus appliance list (name, watts, hours per day)
Examples:
"How much solar did we make?" -> one_day_numbers
"Was the transformer overloaded on 2026-03-23?" -> one_day_numbers
"What was the peak load on March 17?" -> one_day_numbers, day 2026-03-17
"Which 3 days were worst?" -> ranking_of_worst_days
"What bills did people calculate?" -> recent_calculations
day: only if the question names a date (readings run 2026-02-01 to 2026-03-31), otherwise empty.

Question: {q}"""

ANSWER = ("You answer questions from the maintenance engineer of a college campus: transformer TR-MAIN (630 kVA) and a "
          "500 kWp rooftop solar plant. Answer in two or three short sentences using ONLY the data given. "
          "If the data has a status, it was decided by code: repeat it, never change it. Do not calculate anything new.")


def numbers_in(value):
    """Every number in the data (dates and times too), written the same way so they can be compared."""
    if isinstance(value, dict):
        return {n for v in value.values() for n in numbers_in(v)}
    if isinstance(value, list):
        return {n for v in value for n in numbers_in(v)}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {f"{float(value):g}"}
    return {f"{float(n):g}" for n in re.findall(r"\d+(?:\.\d+)?", str(value).replace(",", ""))}


def top_in(q):
    """'Which 3 days…' — an exact number, so code reads it, not the model. Default 5."""
    m = re.search(r"\b([1-9]|1\d|20)\b", q)
    return int(m.group()) if m else 5


def pick_day(q, picked, fallback):
    """A YYYY-MM-DD in the question is an exact pattern, so code reads it. The LLM's day ("March 23") is used only if
    its day number is in the question — otherwise the model made it up — and then the dashboard's day."""
    if m := re.search(r"\d{4}-\d{2}-\d{2}", q):
        return date.fromisoformat(m.group())
    try:
        d = date.fromisoformat(picked)
        if d.day in {int(n) for n in re.findall(r"\d+", q)}:
            return d
    except ValueError:
        pass
    return fallback


@app.get("/ask-data")
def ask_data(q: str = Query(min_length=3, max_length=300, description="a question in plain English"),
             day: date | None = Query(None, description="the day to use if the question names none")):
    """Ask the database a question in plain English; every number in the answer is checked against the data."""
    try:
        p = ask_json(PICK.format(q=q), DataQuestion)                                    # 1. LLM picks the query
    except ValidationError:
        raise HTTPException(status_code=422, detail="Could not work out which data the question needs; try rephrasing.")
    except ConnectionError:
        raise HTTPException(status_code=503, detail="The LLM is not reachable. Locally: start Ollama (ollama pull llama3.2). Deployed: check GROQ_API_KEY.")
    the_day = pick_day(q, p.day, day)
    if p.query == "one_day_numbers":                                                    # 2. code runs it
        if the_day is None:
            raise HTTPException(status_code=400, detail="Which day? Add a date like 2026-03-23.")
        try:
            data = queries.summary(the_day)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        pct = data["peak_loading_pct"]                                                  # the verdict is code's, not the model's
        data["status"] = "OVERLOAD (above 100%)" if pct > 100 else "HIGH (above 80%)" if pct > 80 else "NORMAL (80% or below)"
    elif p.query == "ranking_of_worst_days":
        data = queries.peak_days(top_in(q))
    elif p.query == "recent_calculations":
        data = queries.history(10)
    else:
        data = queries.list_appliances()
    text = ask(f"Question: {q}\nData (from the database): {json.dumps(data, default=str)}", system=ANSWER)   # 3. LLM explains
    listed = re.sub(r"(?m)^\s*\d+[.)]\s", "", text)                                   # "1. 2. 3." list markers aren't data
    bad = sorted(numbers_in(listed) - numbers_in(data) - numbers_in(q) - {"630", "500", "80", "100"})          # 4. code checks
    answer = text if not bad else "LLM answer withheld: it used numbers that are not in the data. The data is below."
    return {"question": q, "query": p.query, "day": str(the_day) if p.query == "one_day_numbers" else None,
            "data": data, "llm_draft": text, "grounded": not bad, "unknown_numbers": bad, "answer": answer}

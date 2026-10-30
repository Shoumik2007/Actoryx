"""Day 2 — the API now has a database: it remembers every calculation and serves two months of substation readings.
First:  python 02_load_readings.py
Run:    uvicorn app:app --reload        → http://127.0.0.1:8000/docs"""
import threading
from datetime import date, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Query

import agent
import appliance
import ee
import queries
from explain import explain_day

app = FastAPI(title="Campus Energy API", version="day-5")


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


@app.get("/peak-days")
def peak_days(top: int = Query(5, ge=1, le=20)):
    """Days when the transformer worked hardest."""
    return queries.peak_days(top)


@app.get("/explain")
def explain(day: date):
    """Two plain sentences about a day, written by the LLM from facts computed by code — and checked by code."""
    try:
        return explain_day(day)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Day 5: the agent replaces /ask-data. It reaches the data through the MCP tools (tools.py → mcp_server.py) ────────
AGENT_LOCK = threading.Lock()                                       # agent.py keeps the last run in globals: one run at a time


def with_day(q, day):
    """A question about 'the day' with no date in it means the day picked on the dashboard. Code adds it, not the model.
    A comparison that names one day is compared with the picked day."""
    tools, named = agent.relevant_tools(q), agent.days_in(q)
    if day and tools == ["compare_days"] and len(named) == 1 and str(day) not in named:
        return f"{q} (and {day})"
    if day and not named and (tools in (["get_summary"], ["get_explanation"]) or len(tools) == len(agent.TOOLS)):
        return f"{q} (on {day})"
    return q


@app.get("/ask-agent")
def ask_agent(q: str = Query(min_length=3, max_length=300, description="a question in plain English"),
              day: date | None = Query(None, description="the day to use if the question names none")):
    """Ask the agent a question; it calls the MCP tools, and code checks every number in its answer."""
    question = with_day(q, day)
    with AGENT_LOCK:
        try:
            answer = agent.run(question, verbose=False)
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"The LLM is not reachable. Locally: start Ollama (ollama pull llama3.2). With Groq: check GROQ_API_KEY. Reason: {str(e)[:300]}")
        observations, evidence = list(agent.LAST_OBSERVATIONS), agent.LAST_EVIDENCE
    if answer is None:
        raise HTTPException(status_code=422, detail="The agent could not answer that with its tools; try rephrasing or name a date.")
    return {"question": q, "asked_as": question, "answer": answer, "grounded": not answer.startswith("(no reliable answer"),
            "tools": [o["action"] for o in observations if "action" in o], "observations": observations, "evidence": evidence}

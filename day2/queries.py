"""queries.py — questions we ask the database. The API, the UI, the agent and the MCP server all use THESE functions."""
from datetime import date, datetime, timedelta

from sqlalchemy import select

from db import ApplianceRow, Calculation, Reading, Session

RATING_KVA, PF = 630, 0.93                                          # TR-MAIN nameplate, campus power factor


def save_calculation(kind, inputs, result):
    with Session() as s:
        s.add(Calculation(kind=kind, inputs=inputs, result=result))
        s.commit()


def history(limit=10):
    with Session() as s:
        rows = s.scalars(select(Calculation).order_by(Calculation.id.desc()).limit(limit))
        return [{"id": c.id, "kind": c.kind, "inputs": c.inputs, "result": c.result, "at": c.created_at.isoformat(timespec="seconds")} for c in rows]


def readings(start: datetime, end: datetime):
    with Session() as s:
        rows = s.scalars(select(Reading).where(Reading.timestamp >= start, Reading.timestamp < end).order_by(Reading.timestamp))
        return [{"timestamp": r.timestamp.isoformat(), "load_kw": r.load_kw, "solar_kw": r.solar_kw, "ambient_c": r.ambient_c} for r in rows]


def loading(r):
    """Transformer loading: solar on the 433 V bus supplies part of the load, so TR-MAIN carries only the net."""
    return max(r["load_kw"] - r["solar_kw"], 0) / PF / RATING_KVA


def summary(day: date):
    rows = readings(datetime.combine(day, datetime.min.time()), datetime.combine(day + timedelta(days=1), datetime.min.time()))
    if not rows:
        raise ValueError(f"no readings for {day}")
    peak = max(rows, key=lambda r: r["load_kw"])
    worst = max(rows, key=loading)
    return {"day": str(day), "readings": len(rows),
            "peak_load_kw": peak["load_kw"], "peak_load_time": peak["timestamp"][11:16],
            "load_kwh": round(sum(r["load_kw"] for r in rows) * 0.25), "solar_kwh": round(sum(r["solar_kw"] for r in rows) * 0.25),
            "peak_loading_pct": round(100 * loading(worst), 1), "peak_loading_time": worst["timestamp"][11:16],
            "max_air_c": max(r["ambient_c"] for r in rows)}


# ── Monday's appliance list, now in the database ────────────────────────────────────────────────────
def _appliance(row):
    return {"id": row.id, "name": row.name, "watts": row.watts, "hours": row.hours}


def list_appliances():
    with Session() as s:
        return [_appliance(r) for r in s.scalars(select(ApplianceRow).order_by(ApplianceRow.id))]


def get_appliance(appliance_id):
    with Session() as s:
        row = s.get(ApplianceRow, appliance_id)
        return _appliance(row) if row else None


def add_appliance(name, watts, hours):
    with Session() as s:
        row = ApplianceRow(name=name, watts=watts, hours=hours)
        s.add(row)
        s.commit()
        return _appliance(row)


def update_appliance(appliance_id, name, watts, hours):
    with Session() as s:
        row = s.get(ApplianceRow, appliance_id)
        if row is None:
            return None
        row.name, row.watts, row.hours = name, watts, hours
        s.commit()
        return _appliance(row)


def delete_appliance(appliance_id):
    with Session() as s:
        row = s.get(ApplianceRow, appliance_id)
        if row is None:
            return False
        s.delete(row)
        s.commit()
        return True


def peak_days(top=10):
    """TASK: the `top` days with the highest transformer loading, highest first.
    Return a list like [{"day": "2026-02-24", "peak_loading_pct": 113.0, "time": "12:30"}, ...]"""
    # TODO 1: read ALL readings (readings(start, end) with a wide range, or a select(Reading))
    # TODO 2: for each day keep the reading with the highest loading(r)
    # TODO 3: sort the days by that loading, highest first, and return the first `top`
    rows = readings(datetime(2026, 1, 1), datetime(2026, 4, 1))          # TODO 1: every reading
    worst = {}
    for r in rows:                                                       # TODO 2: worst reading per day
        day = r["timestamp"][:10]
        if day not in worst or loading(r) > loading(worst[day]):
            worst[day] = r
    best = sorted(worst.values(), key=loading, reverse=True)[:top]       # TODO 3: highest first, keep `top`
    return [{"day": r["timestamp"][:10], "peak_loading_pct": round(100 * loading(r), 1), "time": r["timestamp"][11:16]}
            for r in best]
    

def peak_days(top=5):
    """TASK: the `top` days with the highest transformer loading, highest first.
    Return a list like [{"day": "2026-02-24", "peak_loading_pct": 113.0, "time": "12:30"}, ...]"""
    rows = readings(datetime(2026, 1, 1), datetime(2026, 4, 1))          # TODO 1: every reading
    worst = {}
    for r in rows:                                                       # TODO 2: worst reading per day
        day = r["timestamp"][:10]
        if day not in worst or loading(r) > loading(worst[day]):
            worst[day] = r
    best = sorted(worst.values(), key=loading, reverse=True)[:top]       # TODO 3: highest first, keep `top`
    return [{"day": r["timestamp"][:10], "peak_loading_pct": round(100 * loading(r), 1), "time": r["timestamp"][11:16]}
            for r in best]
    

if __name__ == "__main__":
    for d in peak_days(top=10):
        print(d)



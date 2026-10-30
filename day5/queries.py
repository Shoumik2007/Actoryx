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


def with_status(day: date):
    """One day's numbers plus the OVERLOAD / HIGH / NORMAL verdict — code's, not the model's."""
    s = summary(day)
    pct = s["peak_loading_pct"]
    s["status"] = "OVERLOAD" if pct > 100 else "HIGH" if pct > 80 else "NORMAL"
    return s


def compare_days(days):
    """The same numbers for several days, side by side. The comparison is code's too."""
    rows = [with_status(d) for d in days]
    hi = max(rows, key=lambda r: r["peak_loading_pct"])
    lo = min(rows, key=lambda r: r["peak_loading_pct"])
    return {"days": rows, "highest_loading_day": hi["day"], "lowest_loading_day": lo["day"],
            "difference_pct_points": round(hi["peak_loading_pct"] - lo["peak_loading_pct"], 1)}


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


def peak_days(top=5):
    """The `top` days with the highest transformer loading, highest first."""
    best = {}
    for r in readings(datetime(2000, 1, 1), datetime(2100, 1, 1)):
        day = r["timestamp"][:10]
        if day not in best or loading(r) > loading(best[day]):
            best[day] = r
    ranked = sorted(best.items(), key=lambda kv: -loading(kv[1]))[:top]
    return [{"day": d, "peak_loading_pct": round(100 * loading(r), 1), "time": r["timestamp"][11:16], "air_c": r["ambient_c"]} for d, r in ranked]

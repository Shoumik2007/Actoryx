"""tools.py — the agent's tools are the tools on YOUR MCP server (mcp_server.py), called over MCP.
Each tool has a name, a one-line description (the model reads it) and a function."""
import asyncio
import json

from mcp import Client

from mcp_server import mcp


async def _call_async(name, args):
    async with Client(mcp) as client:
        return await client.call_tool(name, args)


def _call(name, **args):
    result = asyncio.run(_call_async(name, args))
    if result.is_error:
        text = result.content[0].text.split("[type=")[0].strip()           # just the message: the model reads this, and the number check too
        return {"error": text.splitlines()[-1].split(": ", 1)[-1].strip()}
    data = [json.loads(c.text) for c in result.content]                    # a list comes back as several items
    return data[0] if len(data) == 1 else data


def _rows(key, r):
    """A list tool's result under one name, whether it came back as no items, one item or several."""
    return r if isinstance(r, dict) and "error" in r else {key: r if isinstance(r, list) else [r]}


def get_summary(day: str):
    return _call("day_summary", day=day)      # the verdict (status) is a comparison, so the server's CODE adds it


def compare_days(days: list):
    return _call("compare_days", days=days)


def get_peak_days(top: int):
    return _rows("peak_days", _call("peak_days", top=top))


def recent_calculations():
    return _rows("calculations", _call("recent_calculations"))


def appliance_list():
    return _rows("appliances", _call("appliance_list"))


def energy_cost(watts: float, hours: float, rate: float):
    return _call("energy_cost", watts=watts, hours=hours, rate=rate)


def monthly_bill(units: float):
    r = _call("monthly_bill", units=units)
    return r if "error" in r else {"units": r["units"], "bill_rs": r["bill_rs"]}

def get_explanation(day: str):
    r = _call("get_explanation", day=day)
    return r if "error" in r else {"day": day, "answer": r["answer"]}



TOOLS = {
    "get_summary": (get_summary, "one day's numbers for transformer TR-MAIN: peak load, peak loading %, status, energy, solar. Needs day as YYYY-MM-DD (data: 2026-02-01 to 2026-03-31)"),
    "compare_days": (compare_days, "the same numbers for two or more named days, side by side, with the highest and lowest loading day (code reads the dates)"),
    "get_peak_days": (get_peak_days, "the days the transformer worked hardest, highest first. Needs top (how many days)"),
    "recent_calculations": (recent_calculations, "calculations people already asked for (bills, appliance energy cost), newest first"),
    "appliance_list": (appliance_list, "the campus appliance list: name, watts, hours per day"),
    "energy_cost": (energy_cost, "units (kWh) and ₹ cost of running an appliance. Needs watts and hours (code reads the ₹ rate)"),
    "monthly_bill": (monthly_bill, "the monthly electricity bill in ₹ for a number of units (slab tariff). Needs units"),
    "get_explanation": (get_explanation, "two plain sentences explaining a day. Needs day as YYYY-MM-DD (data: 2026-02-01 to 2026-03-31)"),

}

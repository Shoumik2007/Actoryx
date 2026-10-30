"""mcp_server.py — the SAME logic as the API (ee.py + queries.py), published as MCP tools.
REST is the door for people and programs; MCP is the door for AI apps (Claude Desktop, Cursor, your own agent).
Run for Claude Desktop (stdio):    python mcp_server.py
Run over HTTP:                      python mcp_server.py http      → http://127.0.0.1:8001/mcp
Inspect it:                         npx -y @modelcontextprotocol/inspector   (connect to the HTTP URL)"""
import logging
import sys
from datetime import date
from typing import Annotated
from explain import explain_day 

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

import ee
import queries

for noisy in ("httpx", "mcp"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

mcp = MCPServer("campus-energy", instructions="Tools for the campus substation TR-MAIN (630 kVA) and EE calculations.")


@mcp.tool()
def energy_cost(watts: Annotated[float, Field(gt=0, le=50000, description="appliance power in watts (1 kW = 1000 W)")],
                hours: Annotated[float, Field(gt=0, le=24, description="hours of use in a day")],
                rate: Annotated[float, Field(gt=0, le=50, description="₹ per unit (kWh)")] = 8.0) -> dict:
    """Units (kWh) and ₹ cost of running an appliance."""
    result = ee.energy_cost(watts, hours, rate)
    queries.save_calculation("energy-cost", {"watts": watts, "hours": hours, "rate": rate}, result)
    return result


@mcp.tool()
def monthly_bill(units: Annotated[float, Field(ge=0, le=100000, description="units (kWh) used in the month")]) -> dict:
    """The monthly electricity bill in ₹, slab by slab."""
    result = ee.monthly_bill(units)
    queries.save_calculation("bill", {"units": units}, {"bill_rs": result["bill_rs"]})
    return result


@mcp.tool()
def day_summary(day: Annotated[date, Field(description="a day between 2026-02-01 and 2026-03-31, YYYY-MM-DD")]) -> dict:
    """One day for transformer TR-MAIN: peak load, peak loading % (after solar), status, energy, solar, hottest air."""
    try:
        return queries.with_status(day)
    except ValueError as e:
        raise ToolError(str(e))                 # a ToolError's message reaches the client; other exceptions are hidden


@mcp.tool()
def compare_days(days: Annotated[list[date], Field(min_length=2, max_length=7, description="two to seven days between 2026-02-01 and 2026-03-31, YYYY-MM-DD")]) -> dict:
    """The same numbers for several days side by side, with the highest and lowest loading day and the difference."""
    try:
        return queries.compare_days(days)
    except ValueError as e:
        raise ToolError(str(e))


@mcp.tool()
def peak_days(top: Annotated[int, Field(ge=1, le=20, description="how many days")] = 5) -> list:
    """The days transformer TR-MAIN worked hardest, highest loading first."""
    return queries.peak_days(top)


@mcp.tool()
def recent_calculations(limit: Annotated[int, Field(ge=1, le=100, description="how many calculations")] = 10) -> list:
    """Calculations people asked for (bills, appliance energy cost), newest first."""
    return queries.history(limit)


@mcp.tool()
def appliance_list() -> list:
    """The campus appliance list: name, watts and hours per day."""
    return queries.list_appliances()

@mcp.tool()
def get_explanation(day: Annotated[date, Field(description="a day between 2026-02-01 and 2026-03-31, YYYY-MM-DD")]) -> dict:
    """Two plain sentences about a day, written by the LLM from facts computed by code and checked by code."""
    try:
        return explain_day(day)
    except ValueError as e:
        raise ToolError(str(e))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        mcp.run(transport="streamable-http", port=8001)
    else:
        mcp.run()

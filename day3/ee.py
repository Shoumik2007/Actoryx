"""ee.py — the logic, in ONE place. The API (app.py) only calls these functions."""


def calculate(a: float, b: float, op: str) -> float:
    if op == "add":
        return a + b
    if op == "sub":
        return a - b
    if op == "mul":
        return a * b
    if op == "div":
        if b == 0:
            raise ValueError("cannot divide by zero")
        return a / b
    raise ValueError(f"unknown operation '{op}' — use add, sub, mul or div")


def energy_cost(watts: float, hours: float, rate: float = 8.0) -> dict:
    """Units (kWh) and cost (₹) of running an appliance of `watts` for `hours`, at `rate` rupees per unit."""
    if watts <= 0 or not 0 < hours <= 24 or rate <= 0:
        raise ValueError("watts and rate must be positive, hours between 0 and 24")
    units = watts * hours / 1000                 # W × h = Wh; ÷ 1000 = kWh = units
    return {"units": round(units, 2), "cost_rs": round(units * rate, 2)}


# The monthly bill uses slabs: the first units are cheap, later units cost more (illustrative domestic rates).
SLABS = [(100, 3.00), (100, 4.50), (None, 6.50)]   # (units in this slab, ₹ per unit); None = everything above


def monthly_bill(units: float) -> dict:
    """The monthly bill for `units`, slab by slab."""
    if units < 0:
        raise ValueError("units cannot be negative")
    left, parts = units, []
    for size, rate in SLABS:
        used = left if size is None else min(left, size)
        if used <= 0:
            break
        parts.append({"units": used, "rate": rate, "amount": round(used * rate, 2)})
        left -= used
    return {"units": units, "slabs": parts, "bill_rs": round(sum(p["amount"] for p in parts), 2)}

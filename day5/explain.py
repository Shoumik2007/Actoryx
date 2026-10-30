"""explain.py — the API's new skill: code computes the day's facts, the LLM writes two plain sentences about them,
and code CHECKS that every number in those sentences is one of the facts."""
import re
from datetime import date

import queries
from llm import ask

SYSTEM = ("You advise the maintenance engineer of a college campus. In two short sentences say whether the day needs "
          "attention and why. The status line was decided by code — repeat it, never change it. "
          "Use ONLY numbers that appear in the facts. Do not calculate anything new.")


def status(f):
    """The verdict is a comparison — code makes it, not the model."""
    pct = f["peak_loading_pct"]
    return "OVERLOAD (above 100%)" if pct > 100 else "HIGH (above 80%)" if pct > 80 else "NORMAL (80% or below)"


def facts_text(f):
    """The facts as plain sentences, written by code — the model can't misread a key name."""
    return (f"Status: {status(f)}. Peak campus load {f['peak_load_kw']} kW at {f['peak_load_time']}. "
            f"Transformer TR-MAIN peak loading {f['peak_loading_pct']}% of its 630 kVA rating at {f['peak_loading_time']}, after rooftop solar. "
            f"Energy used {f['load_kwh']:,} kWh; solar generated {f['solar_kwh']:,} kWh. Hottest air {f['max_air_c']} °C.")


def ungrounded_numbers(text, facts):
    known = {f"{float(v):g}" for v in facts.values() if isinstance(v, (int, float))}
    known |= {f"{float(n):g}" for v in facts.values() if isinstance(v, str) for n in re.findall(r"\d+(?:\.\d+)?", v)}
    known |= {"630", "80", "100"}
    return [n for n in re.findall(r"\d+(?:\.\d+)?", text.replace(",", "")) if f"{float(n):g}" not in known]


def explain_day(day: date):
    facts = queries.summary(day)                                          # 1. code computes
    written = facts_text(facts)
    text = ask(f"Facts: {written}", system=SYSTEM)                        # 2. LLM explains
    bad = ungrounded_numbers(text, facts)                                 # 3. code checks
    answer = text if not bad else written + "  (LLM explanation withheld: it used numbers that are not in the facts)"
    return {"facts": facts, "facts_text": written, "llm_draft": text, "grounded": not bad, "unknown_numbers": bad,
            "answer": f"{status(facts).split()[0]}: {answer}"}                       # 4. the verdict word is code's

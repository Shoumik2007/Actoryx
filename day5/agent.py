"""agent.py — a small agent: THINK (which tool?) → ACT (code calls the API) → OBSERVE (result) → repeat → ANSWER.
Built for a small local model: each turn the model may ONLY choose from real tools, every argument is validated,
and the final answer may only contain numbers that came from the question or a tool."""
import json
import re
from datetime import date
from typing import Literal, Optional

from pydantic import ValidationError, create_model

import llm
from tools import TOOLS

LAST_EVIDENCE, LAST_OBSERVATIONS = "", []
GUIDE = ("You are an assistant for the campus electrical maintenance team. Answer the question using the tools.\n"
         "Tools:\n" + "\n".join(f"- {name}: {desc}" for name, (_, desc) in TOOLS.items()) +
         "\n- final_answer: when the observations answer the question."
         "\nChoose ONE action per turn. Fill only the arguments that action needs. "
         "As soon as the observations answer the question, choose final_answer.")

ARGS = {"day": (Optional[str], None), "top": (Optional[int], None), "watts": (Optional[float], None),
        "hours": (Optional[float], None), "rate": (Optional[float], None), "units": (Optional[float], None)}
NEEDS = {"get_summary": ["day"], "get_peak_days": ["top"], "energy_cost": ["watts", "hours"],
         "monthly_bill": ["units"], "compare_days": [], "recent_calculations": [], "appliance_list": [], "get_explanation": ["day"]}


MONTHS = r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{4}-\d{2}-\d{2}"
MONTH_NAMES = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
A_MONTH = "|".join(MONTH_NAMES)


def days_in(question):
    """Dates are an exact pattern, so code reads them: 2026-03-23, 23 March, March 23 (the data is all 2026)."""
    found = []
    for m in re.finditer(rf"(\d{{4}}-\d{{2}}-\d{{2}})|\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({A_MONTH})[a-z]*|\b({A_MONTH})[a-z]*\s+(\d{{1,2}})\b", question.lower()):
        try:
            d = m[1] or date(2026, MONTH_NAMES.index(m[3] or m[4]) + 1, int(m[2] or m[5])).isoformat()
        except ValueError:
            continue
        if d not in found:
            found.append(d)
    return found[:7]


def rate_in(question):
    """'₹8 per unit' is an exact pattern: code reads it (default ₹8). The model only has to supply watts and hours."""
    m = re.search(r"₹\s*(\d+(?:\.\d+)?)", question)
    return float(m.group(1)) if m else 8.0


def relevant_tools(question):
    """Code, not the model, decides which tools could possibly help with THIS question."""
    q = question.lower()
    if len(days_in(q)) >= 2 or re.search(r"compar|versus|\bvs\b", q):
        return ["compare_days"]
    if re.search(r"explain|\bwhy\b", q):
        return ["get_explanation"]
    if re.search(r"calculat|bills\b|history", q) and re.search(r"people|anyone|history|recent|past|previous|earlier|so far", q):
        return ["recent_calculations"]
    if "appliance" in q and not re.search(r"\d", q):
        return ["appliance_list"]
    tools = []
    if re.search(MONTHS, q):
        tools.append("get_summary")
    if re.search(r"worst|hardest|highest|which days|top \d|busiest", q):
        tools.append("get_peak_days")
    if re.search(r"\bbill\b|slab|units (this|a|per) month", q):
        tools.append("monthly_bill")
    elif re.search(r"\bcost\b|₹|rupees|\bwatts?\b|\b\d+ ?w\b", q):
        tools.append("energy_cost")
    return tools or list(TOOLS)


def acceptable(answer):
    """A real sentence: has words, not just symbols or a list."""
    return bool(answer) and len(re.findall(r"[A-Za-z]{2,}", answer)) >= 3


def numbers(text):
    return {f"{float(n):g}" for n in re.findall(r"\d+(?:\.\d+)?", str(text).replace(",", ""))}


def run(question, max_steps=5, verbose=True):
    global LAST_EVIDENCE, LAST_OBSERVATIONS
    observations, used = [], set()
    LAST_EVIDENCE, LAST_OBSERVATIONS = "", observations
    candidates = relevant_tools(question)
    for step_no in range(1, max_steps + 1):
        succeeded = any("error" not in o.get("result", {"error": 1}) for o in observations)
        allowed = [t for t in candidates if t not in used] + (["final_answer"] if succeeded else [])   # no answer before evidence
        allowed = allowed or ["final_answer"]
        Step = create_model("Step", thought=(str, ...), action=(Literal[tuple(allowed)], ...), **ARGS)
        state = {"question": question, "observations": observations}
        reply = llm.chat([{"role": "system", "content": GUIDE}, {"role": "user", "content": json.dumps(state)}], schema=Step, limit=300)
        try:
            step = Step.model_validate_json(reply)
        except ValidationError:                                              # Groq isn't held to the schema: refuse the step and let it try again
            observations.append({"error": f"not a valid step: choose one of {allowed}"})
            if verbose:
                print(f"  [{step_no}] refused: not a valid step")
            continue
        if verbose:
            print(f"  [{step_no}] think: {step.thought[:110]}")

        if step.action == "final_answer":
            answer = write_answer(question, observations)                    # a separate, plain-text call writes the sentence
            evidence = numbers(question) | numbers(json.dumps(observations))
            invented = sorted(numbers(answer) - evidence)
            LAST_EVIDENCE = evidence_line(observations)
            if acceptable(answer) and not invented:
                if verbose:
                    print(f"      answer ✓ {answer}")
                    print(f"      evidence (written by code, from the MCP tools): {evidence_line(observations)}")
                return answer
            problem = f"numbers not in the evidence: {invented}" if invented else "not a full sentence"
            if verbose:
                print(f"      answer ✗ rejected ({problem}): {answer!r}")
            return f"(no reliable answer — {problem}) Evidence: {evidence_line(observations)}"

        if step.action in ("get_summary", "get_explanation"):
            step.day = next(iter(days_in(question)), None)                   # code reads the date; the model can't invent one
        missing = [a for a in NEEDS[step.action] if getattr(step, a) is None]
        if missing:
            result = {"error": f"{step.action} needs {missing}"}
        else:
            func = TOOLS[step.action][0]
            args = {a: getattr(step, a) for a in NEEDS[step.action]}
            if step.action == "energy_cost":
                args["rate"] = rate_in(question)                              # code fills what it can read exactly
            if step.action == "compare_days":
                args["days"] = days_in(question)
            if step.action in ("energy_cost", "monthly_bill"):              # calculator inputs must come from the question
                made_up = [a for a, v in args.items() if f"{float(v):g}" not in numbers(question) | numbers(json.dumps(observations))]
                result = {"error": f"these values are not in the question: {made_up}"} if made_up else func(**args)
            else:
                result = func(**args)
            if "error" not in result:
                used.add(step.action)
        observations.append({"action": step.action, "args": {a: getattr(step, a) for a in NEEDS[step.action]}, "result": result})
        if verbose:
            print(f"      act:   {step.action}{observations[-1]['args']}\n      see:   {json.dumps(result)[:150]}")
    return None


def write_answer(question, observations):
    """Deciding WHAT to do and WRITING the answer are separate jobs. Here the model only writes, in plain text."""
    useful = [o for o in observations if "action" in o and "error" not in o["result"]]
    return llm.ask(f"Question: {question}\nTool results: {json.dumps(useful)}",
                   system="Answer the question in one or two sentences for a maintenance engineer. Use only numbers "
                          "that appear in the tool results, copied exactly. If a result has a status, state it.")


def evidence_line(observations):
    """What the tools actually returned, in a fixed format — shown next to the model's sentence."""
    parts = []
    for o in observations:
        r = o.get("result", {})
        if "error" in r or "action" not in o:
            continue
        if o["action"] == "get_summary":
            parts.append(f"{r['day']}: peak loading {r['peak_loading_pct']}% at {r['peak_loading_time']} → {r['status']}")
        elif o["action"] == "get_peak_days":
            parts.append("worst days " + ", ".join(f"{d['day']} ({d['peak_loading_pct']}%)" for d in r["peak_days"]))
        elif o["action"] == "compare_days":
            parts.append(", ".join(f"{d['day']}: {d['peak_loading_pct']}% → {d['status']}" for d in r["days"]) +
                         f"; highest {r['highest_loading_day']}, {r['difference_pct_points']} points above lowest")
        elif o["action"] == "recent_calculations":
            parts.append("recent calculations: " + (", ".join(f"{c['kind']} {c['inputs']} → {c['result']}" for c in r["calculations"]) or "none"))
        elif o["action"] == "appliance_list":
            parts.append("appliances: " + (", ".join(f"{a['name']} ({a['watts']} W, {a['hours']} h)" for a in r["appliances"]) or "none"))
        else:
            parts.append(f"{o['action']} → {r}")
    return " · ".join(parts)

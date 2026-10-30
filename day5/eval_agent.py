"""Day 5 task — test your agent like an engineer tests a relay: known inputs, expected outputs, a score.
Copy this file into ../code and run:  python eval_agent.py
TODO 1: add a tool `get_explanation(day)` in tools.py that calls GET /explain and returns its "answer";
        teach relevant_tools() in agent.py when to offer it (e.g. the question says "explain" or "why").
TODO 2: add three more test cases below — at least one that the agent should NOT be able to answer."""
import agent

TESTS = [  # (question, the tool it must use, a number that must appear in the answer or evidence)
    ("What was the peak loading on 17 March 2026?", "get_summary", "109.8"),
    ("Which five days did the transformer work hardest?", "get_peak_days", "98.1"),
    ("What is the bill for 410 units this month?", "monthly_bill", "2115"),
    ("Compare the loading on 2026-03-17 and 2026-03-23", "compare_days", "106.4"),
    ("What bills did people calculate?", "recent_calculations", "2115"),
    ("What appliances are on the campus list?", "appliance_list", "appliances:"),
    
    # TODO 2: add one test the agent should NOT be able to answer
    ("Explain the transformer's loading on 23 March 2026.", "get_explanation", "2026-03-23"),
    ("What was the peak loading on 2027-01-01?", "get_summary", None),   # no data for that day


]


def traced(name, f, calls):
    """Wrap a tool so we can see which tools the agent actually called."""
    def wrapper(**kwargs):
        calls.append(name)
        return f(**kwargs)
    return wrapper


original = dict(agent.TOOLS)
passed = accepted = 0
for question, tool, must_see in TESTS:
    calls = []
    for name, (f, desc) in original.items():
        agent.TOOLS[name] = (traced(name, f, calls), desc)
    answer = agent.run(question, verbose=False) or ""
    ok = tool in calls and (not answer if must_see is None else must_see in answer + agent.LAST_EVIDENCE)
    passed += ok
    accepted += bool(answer) and not answer.startswith("(no reliable")
    print(f"{'✓' if ok else '✗'} {question[:52]:<53} tools {calls}  answer: {answer[:80]}")
print(f"\n{passed} / {len(TESTS)} passed (right tool, right evidence) · {accepted} sentences accepted by the number check")
print("Discuss: a test can pass while the sentence is still wrong — what else would you check?")

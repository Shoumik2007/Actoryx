"""Day 5 · Step 3 — the agent answers maintenance questions by calling YOUR MCP server.
Run:  python 01_run_agent.py      (Ollama must be running)"""
import agent

for q in ["What was the transformer's peak loading on 23 March 2026, and was it overloaded?",
          "Which three days did the transformer work hardest?",
          "A 1500 W AC runs 8 hours a day. At ₹8 per unit, what does it cost per day?"]:
    print(f"\nQ: {q}")
    agent.run(q)

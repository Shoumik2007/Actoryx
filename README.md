# Actoryx — Campus Energy API

A campus energy API for a college with a 630 kVA transformer (TR-MAIN) and a 500 kWp rooftop solar plant, built up day by day: a [FastAPI](https://fastapi.tiangolo.com/) API, then a database and cloud deployment, a [Streamlit](https://streamlit.io/) dashboard, then an LLM (llama3.2 locally via [Ollama](https://ollama.com), or [Groq](https://groq.com) in the cloud), and finally an agent that gets its data through [MCP](https://modelcontextprotocol.io) tools.

| Day | Folder | What it adds | Live |
|---|---|---|---|
| 1 | root (`app.py`, `ee.py`) | Calculator and energy-cost API | — |
| 2 | [`day2/`](day2) | SQLite database, substation readings, deployment | [API docs](https://campus-energy-api.fastapicloud.dev/docs) |
| 3 | [`day3/`](day3) | Streamlit calculator and dashboard | [Dashboard](https://campus-energy-dashboard.streamlit.app) |
| 4 | [`day4/`](day4) | SCADA alarms classified by llama3.2 | Local only |
| 4 | [`day4_dashboard/`](day4_dashboard) | Ask the dashboard questions in plain English (Groq or Ollama) | [Dashboard](https://campus-energy-llm.streamlit.app) · [API docs](https://campus-energy-day4.fastapicloud.dev/docs) |
| 5 | [`day5/`](day5) | An agent on the dashboard, using MCP tools (Groq or Ollama) | [Dashboard](https://campus-energy-mcp.streamlit.app) · [API docs](https://campus-energy-mcp.fastapicloud.dev/docs) |

Each folder runs on its own. See its section below.

## Day 1 — the API (root folder)

A calculator and an appliance energy-cost calculator, served as a web API.

### Files

| File | What it does |
|---|---|
| `app.py` | The API: defines the endpoints and calls the logic in `ee.py` |
| `ee.py` | The logic: `calculate`, `energy_cost`, and `monthly_bill` (stretch, not finished) |
| `appliance.py` | Reference only: example of a pydantic model (`Appliance`) used to validate a JSON body. Not used by `app.py` |

### Setup

```bash
pip install fastapi uvicorn
uvicorn app:app --reload
```

Then open http://127.0.0.1:8000/docs for the interactive docs.

### Endpoints

| Method | Path | Example | Result |
|---|---|---|---|
| GET | `/` | `/` | Health message |
| GET | `/calculate` | `/calculate?a=12&b=3&op=div` | `4.0` (`op` is `add`, `sub`, `mul` or `div`; dividing by zero returns 400) |
| GET | `/energy-cost` | `/energy-cost?watts=1500&hours=8` | 12 units, ₹96 |
| POST | `/energy-cost` | body `{"watts": 75, "hours": 10}` | 0.75 units, ₹6 |

Energy cost inputs are checked: watts 0–50,000, hours 0–24, rate 0–50 ₹/unit (default ₹8). Values outside these limits return 422.

Units are kWh: `watts × hours ÷ 1000`. Cost is `units × rate`.

### Assignment status

- [x] TODO 1: `GET /energy-cost`
- [x] TODO 2: `POST /energy-cost`
- [ ] Stretch: `GET /appliances/{appliance_id}/cost`
- [ ] Stretch: `GET /bill?units=250` (slab tariff)

## Day 2 — database + deployment (`day2/`)

**Live:** https://campus-energy-api.fastapicloud.dev — interactive docs at https://campus-energy-api.fastapicloud.dev/docs

The API now stores data in SQLite (SQLAlchemy): every calculation is saved, and two months of substation readings (Feb–Mar 2026, one every 15 minutes) are loaded from `campus_feb_mar_2026.csv`. On a fresh server the readings table is filled automatically at startup.

| Method | Path | Example | Result |
|---|---|---|---|
| GET | `/history` | `/history?limit=10` | Most recent calculations, newest first |
| GET | `/readings` | `/readings?start=2026-03-23T00:00&end=2026-03-24T00:00` | Readings in that time window |
| GET | `/summary` | `/summary?day=2026-02-24` | Peak load, energy, solar and peak transformer loading for one day |
| GET | `/peak-days` | `/peak-days?top=5` | The days the transformer was loaded hardest, highest first (`top` 1–20) |

Run locally:

```bash
cd day2
python 02_load_readings.py
uvicorn app:app --reload
```

Deploy (FastAPI Cloud): `cd day2 && fastapi deploy`

## Day 3 — a UI on the API (`day3/`)

**Live dashboard:** https://campus-energy-dashboard.streamlit.app (the calculator page runs locally only)

Two [Streamlit](https://streamlit.io/) pages for people who don't write code. The pages do no maths: every number comes from the API (the same code as Day 2), which reads the database.

| File | What it does |
|---|---|
| `ui_calculator.py` | Three tabs (calculator, energy cost, bill) and a history table. Shows the API's own error messages |
| `dashboard.py` | Pick a day: peak load, energy, solar, transformer loading, a load vs solar chart and the five hardest days |
| `test_ui.py` | Starts the API and runs both pages with Streamlit's `AppTest`, without a browser |

**Task — status banner:** the dashboard shows a red OVERLOAD banner above 100% transformer loading, amber HIGH above 80%, and green NORMAL otherwise, with the time it happened. The thresholds are TR-MAIN's operating limits.

| Day | Banner | Screenshot |
|---|---|---|
| 23 March | 🔴 OVERLOAD 106.4% at 12:45 | [banner_2026-03-23.jpg](day3/banner_2026-03-23.jpg) |
| 4 March (Holi) | 🟢 NORMAL 67.1% at 20:15 | [banner_2026-03-04.jpg](day3/banner_2026-03-04.jpg) |

Run locally (two terminals):

```bash
cd day3
pip install -r requirements.txt
uvicorn app:app --reload         # terminal 1: the API
streamlit run dashboard.py       # terminal 2: or ui_calculator.py
```

Test both pages: `cd day3 && python test_ui.py`

The pages call the API at `API_URL`, which defaults to `http://127.0.0.1:8000`.

Deploy (Streamlit Community Cloud): on https://share.streamlit.io, create an app from this repo, branch `main`, main file `day3/dashboard.py` (or `day3/ui_calculator.py`). Under **Advanced settings → Secrets** add:

```toml
API_URL = "https://campus-energy-api.fastapicloud.dev"
```

## Day 4 — SCADA alarms with a local LLM (`day4/`)

Free-text SCADA alarms are turned into structured JSON that a program can sort and count. The model runs locally with [Ollama](https://ollama.com) (`llama3.2`): no API keys, and nothing leaves the laptop.

| File | What it does |
|---|---|
| `llm.py` | Small wrapper around Ollama: `ask()` for text, `ask_json()` for a reply that must match a pydantic model |
| `classify_alarms.py` | Classifies each alarm into an `Alarm` model (equipment, category, severity) and scores it against the labels |
| `alarms.csv` | 16 alarm messages from a campus solar + substation system, each with its correct category |

**Categories:** protection, communication, power quality, equipment health. **Severity:** critical, warning, info. The prompt explains each category in one line, and `temperature=0` with a fixed seed gives the same answers on every run.

**Score: 15 of 16.** The only miss: "pyranometer reading frozen at 812 W/m2" is labelled communication (a stuck reading), but the model calls it equipment health.

Run locally:

```bash
ollama pull llama3.2             # once
cd day4
pip install -r requirements.txt
python classify_alarms.py
```

## Day 4 — an LLM on the Streamlit dashboard (`day4_dashboard/`)

**Live dashboard:** https://campus-energy-llm.streamlit.app — API at https://campus-energy-day4.fastapicloud.dev ([docs](https://campus-energy-day4.fastapicloud.dev/docs)). The deployed version uses Groq.

The Day 3 dashboard gets a chat box: ask the database a question in plain English, answered by an LLM: Groq's cloud API when `GROQ_API_KEY` is set, otherwise `llama3.2` running locally through Ollama. The model never does the maths. It only chooses which query to run and puts the result into words.

How `GET /ask-data?q=...&day=...` answers a question:

1. **LLM picks the query:** one day's numbers, the worst days ranking, recent calculations, or the appliance list.
2. **Code runs it** on the database. Dates and "top N" are read from the question by code, and the OVERLOAD / HIGH / NORMAL status is decided by code, not by the model.
3. **LLM explains** the result in two or three sentences.
4. **Code checks every number** in the answer against the data. If the model used a number that isn't there, the answer is withheld and the raw data is shown instead.

| File | What it does |
|---|---|
| `app.py` | The Day 2 API plus the `/ask-data` endpoint |
| `dashboard.py` | The Day 3 dashboard plus the chat box |
| `llm.py` | The Day 4 wrapper (`ask`, `ask_json`) with two backends: Groq if `GROQ_API_KEY` is set, otherwise Ollama |

Run locally (two terminals, with Ollama running):

```bash
ollama pull llama3.2             # once
cd day4_dashboard
pip install -r requirements.txt
uvicorn app:app --reload         # terminal 1: the API
streamlit run dashboard.py       # terminal 2: the dashboard
```

**Choosing the LLM:**

| Setting | Backend | Notes |
|---|---|---|
| No `GROQ_API_KEY` | Ollama, `llama3.2` | Runs on the laptop, no key, nothing leaves the machine |
| `GROQ_API_KEY` set | Groq, `openai/gpt-oss-20b` | Free key from https://console.groq.com. Change the model with `GROQ_MODEL` |

To use Groq locally, set the key before starting the API (never commit it):

```bash
export GROQ_API_KEY=...          # your key
uvicorn app:app --reload
```

When deploying, add `GROQ_API_KEY` as a secret or environment variable on the host instead.

**Deployment:** the API and the dashboard are deployed separately from Day 2 and Day 3, so those stay unchanged.

1. API (FastAPI Cloud), app `campus-energy-day4`:

   ```bash
   cd day4_dashboard
   fastapi deploy
   fastapi cloud env set GROQ_API_KEY --value-stdin --secret   # paste the key, then Ctrl+D
   ```

2. Dashboard (Streamlit Community Cloud): an app from this repo, branch `main`, main file `day4_dashboard/dashboard.py`. Under **Settings → Secrets** add the line below, then reboot the app:

   ```toml
   API_URL = "https://campus-energy-day4.fastapicloud.dev"
   ```

   If the dashboard says the API is not running, `API_URL` is missing or wrong, so it falls back to `http://127.0.0.1:8000`.

If the LLM can't be reached (Ollama not running, or a bad Groq key, rate limit or no internet), `/ask-data` returns 503 with a message saying which to check.

## Day 5 — an agent that works through MCP (`day5/`)

**Live dashboard:** https://campus-energy-mcp.streamlit.app — API at https://campus-energy-mcp.fastapicloud.dev ([docs](https://campus-energy-mcp.fastapicloud.dev/docs)). The deployed version uses Groq.

The dashboard's chat box now talks to an agent instead of `/ask-data`. The agent decides which tools to call, and it reaches the data only through the tools on an [MCP](https://modelcontextprotocol.io) server. The same server can also be used by other MCP clients, such as Claude Code.

```
dashboard.py → GET /ask-agent → agent.py ⇄ LLM (Groq or Ollama)
                                   ↓
                     tools.py (MCP client) → mcp_server.py → queries.py / ee.py → database
```

The MCP client and server run inside the API process and talk in memory, so the deployed app has no public `/mcp` address. The other dashboard panels call the REST endpoints directly.

How `GET /ask-agent?q=...&day=...` answers a question:

1. **Code narrows the choice:** it works out which tools could help with this question, and the model may only pick from those.
2. **LLM picks a tool:** each step is validated. A step that isn't allowed is refused and the model tries again, up to 5 steps.
3. **Code fills in what it can read exactly:** dates, the ₹ rate, and the units for a bill on a named day. Calculator inputs the model supplies must appear in the question or a tool result.
4. **The MCP server runs the tool** and returns the result, including the OVERLOAD / HIGH / NORMAL status, which code decides.
5. **LLM writes the answer**, then **code checks every number** against the question and the tool results. If a number isn't there, the sentence is rejected and only the evidence is shown.

The dashboard shows a code-written evidence line and the tool calls under each answer. Check the sentence against them: the number check can't tell when a real number is described wrongly.

### MCP tools

| Tool | What it does |
|---|---|
| `day_summary` | One day's peak load, peak loading %, status, energy, solar and hottest air |
| `compare_days` | The same numbers for 2 to 7 days, with the highest and lowest loading day |
| `peak_days` | The days the transformer worked hardest |
| `get_explanation` | Two plain sentences about a day, written by the LLM and checked by code |
| `energy_cost` | Units and ₹ cost of running an appliance |
| `monthly_bill` | The monthly bill for a number of units (slab tariff) |
| `recent_calculations` | Calculations already made, newest first |
| `appliance_list` | The campus appliance list |

### Files

| File | What it does |
|---|---|
| `agent.py` | The agent loop and its guardrails |
| `tools.py` | The agent's tools, each calling the MCP server through an MCP client |
| `mcp_server.py` | The MCP server: `ee.py` and `queries.py` published as tools |
| `llm.py` | Two backends: Groq if `GROQ_API_KEY` is set, otherwise Ollama |
| `app.py` | The API plus the `/ask-agent` endpoint |
| `dashboard.py` | The Day 4 dashboard, with the chat box now calling the agent |
| `eval_agent.py` | 8 test questions, scored on the right tool and the right evidence |
| `01_run_agent.py` | Runs the agent on three questions in the terminal, without the API |

### Run locally

```bash
cd day5
pip install -r requirements.txt
export GROQ_API_KEY=...          # optional: without it, run Ollama (ollama pull llama3.2)
uvicorn app:app --reload         # terminal 1: the API
streamlit run dashboard.py       # terminal 2: the dashboard
```

Test the agent (Groq's free tier may rate-limit a full run; if so, wait a minute and retry):

```bash
python eval_agent.py
```

To use the tools from Claude Code, register the server from `day5/` with the full path to your Python and to `mcp_server.py`, then approve it when you next start Claude Code:

```bash
claude mcp add --scope project campus-energy -- /full/path/to/python3 /full/path/to/day5/mcp_server.py
```

### Deployment

1. API (FastAPI Cloud):

   ```bash
   cd day5
   fastapi deploy
   fastapi cloud env set GROQ_API_KEY --value-stdin --secret   # paste the key, press Enter, then Ctrl+D
   fastapi deploy                                              # so the running app picks up the key
   ```

   The readings table is filled from `campus_feb_mar_2026.csv` on a fresh server. History and appliances are kept in that server's SQLite file, so they may not survive a redeploy.

2. Dashboard (Streamlit Community Cloud): an app from this repo, branch `main`, main file `day5/dashboard.py`. Under **Settings → Secrets** add the line below, then reboot the app. The Groq key goes on the API, not here.

   ```toml
   API_URL = "https://campus-energy-mcp.fastapicloud.dev"
   ```

### Known limits

- **Bills for one day are estimates:** the slab tariff is monthly, so a bill on a named day applies it to that day's energy, before solar, and the answer says so.
- **Date formats:** `2026-03-04`, `March 4th` and `4 March` are understood. `the 4th of March` is not.
- **The eval doesn't check wording:** it can pass while a sentence is misleading, so read the answers as well as the score.
- **Answers need the key on Groq:** if the LLM can't be reached, or Groq rejects a request, `/ask-agent` returns 503 with the reason.

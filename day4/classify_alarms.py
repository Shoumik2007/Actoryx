"""Day 4 task — turn free-text SCADA alarms into structured JSON a program can sort and count.
Copy llm.py next to this file (or run it from ../../code). Run:  python classify_alarms.py"""
from typing import Literal

import pandas as pd
from pydantic import BaseModel

from llm import ask_json


class Alarm(BaseModel):
    equipment: str                       # e.g. "INV-07", "TR-1", "CB-2"
    category: Literal["protection", "communication", "power quality", "equipment health"]   # TODO 1
    severity: Literal["critical", "warning", "info"]                                         # TODO 2


alarms = pd.read_csv("alarms.csv")
correct = 0
for row in alarms.itertuples():
    # TODO 3: explain the four categories in one line each, then the alarm text
    prompt = f"""Classify this SCADA alarm from a campus solar + substation system.
Categories:
- protection: something tripped, opened or was isolated to protect the system (relay, breaker, contactor, inverter trip); any relay alarm (e.g. Buchholz) counts as protection
- communication: data is missing or wrong because of the link or the sensor: connection lost, timeout, polls missed, or a reading frozen/stuck at one value
- power quality: voltage, current, frequency or harmonics outside normal limits
- equipment health: the device itself is wearing out or running hot (temperature, insulation, battery cells, fan); not used for trips or for data/reading problems
Equipment is the tag of the device, e.g. INV-07, TR-2, CB-2.

Alarm: {row.message}"""
    result = ask_json(prompt, Alarm)
    print(f"{result.category:<17} {result.severity:<9} {result.equipment:<10} {row.message[:60]}")
    # TODO 4: count how many categories match the 'category' column
    if result.category == row.category:
        correct += 1

print(f"\nScore: {correct} of {len(alarms)}")

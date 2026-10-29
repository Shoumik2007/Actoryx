"""llm.py — one small wrapper around the local model (Ollama + llama3.2). No API keys, nothing leaves the laptop.
Setup once:  install Ollama from ollama.com, then   ollama pull llama3.2"""
import ollama

MODEL = "llama3.2"                      # on a 4 GB laptop use "llama3.2:1b"
OPTIONS = {"temperature": 0, "seed": 42}  # same question → same answer, so the class sees the same thing


def ask(prompt, system=None):
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    return ollama.chat(model=MODEL, messages=messages, options=OPTIONS).message.content.strip()


def ask_json(prompt, schema):
    """Ask for JSON that must match a pydantic model; returns a validated object (or raises)."""
    reply = ollama.chat(model=MODEL, format=schema.model_json_schema(), options=OPTIONS,
                        messages=[{"role": "user", "content": prompt}])
    return schema.model_validate_json(reply.message.content)

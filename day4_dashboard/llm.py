"""llm.py — one small wrapper around the model. Two backends, same two functions:
- Groq (free cloud API, used when GROQ_API_KEY is set — e.g. in the deployed app). Key from console.groq.com
- Ollama + llama3.2 on this laptop (no key, nothing leaves the laptop). Setup once:  ollama pull llama3.2"""
import json
import os

OPTIONS = {"temperature": 0, "seed": 42}  # same question → same answer, so the class sees the same thing

if os.environ.get("GROQ_API_KEY"):
    import groq

    MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")     # see console.groq.com/docs/models for the free list
    client = groq.Groq()                                           # reads GROQ_API_KEY

    def chat(messages, json_mode=False):
        try:
            reply = client.chat.completions.create(model=MODEL, messages=messages, **OPTIONS,
                                                   response_format={"type": "json_object"} if json_mode else None)
        except groq.APIError as e:                                 # bad key, rate limit, no internet…
            raise ConnectionError(f"Groq: {e}") from e
        return reply.choices[0].message.content
else:
    import ollama

    MODEL = "llama3.2"                      # on a 4 GB laptop use "llama3.2:1b"

    def chat(messages, json_mode=False):
        return ollama.chat(model=MODEL, messages=messages, options=OPTIONS,
                           format="json" if json_mode else None).message.content


def ask(prompt, system=None):
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    return chat(messages).strip()


def ask_json(prompt, schema):
    """Ask for JSON that must match a pydantic model; returns a validated object (or raises)."""
    prompt += f"\n\nReply with only a JSON object matching this JSON schema:\n{json.dumps(schema.model_json_schema())}"
    return schema.model_validate_json(chat([{"role": "user", "content": prompt}], json_mode=True))
